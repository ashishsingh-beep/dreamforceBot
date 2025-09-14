import os
import streamlit as st
import pandas as pd
from stages.stage_1 import scout_leads
from stages.stage_2 import get_linkedin_profile_details
from stages.stage_3 import evaluate_lead
import io
from supabase import create_client, Client
from dotenv import load_dotenv
import concurrent.futures


# Set up supabase 
load_dotenv()
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# Fetch all linkedin accounts from Supabase

def fetch_lkd_account(status):
    accounts = {}
    all_status = set()
    response = (
        supabase.table("Accounts")
        .select("email_id", "password", "status")
        .eq("status", status)
        .execute()
)
    for item in response.data:
        accounts[item['email_id']] = item['password']
        all_status.add(item['status'])
    return accounts


# Load Linkedin urls from all_leads table for Stage 2 from Supabase
def fetch_urls_from_all_leads(init_range, final_range):
    linkedin_urls = [] 
    response = (
                supabase.table("all_leads")
                .select("linkedin_url")
                .eq("scraped", False)
                .range(init_range, final_range)
                .execute()
                )
    for item in response.data:
        linkedin_urls.append(item['linkedin_url'])
    return linkedin_urls


# Load LinkedIn profile details from lead_details table for Stage 3 from Supabase
lead_details_list = [] 
response = (
    supabase.table("lead_details")
    .select("lead_id", "name", "title", "location", "profile_url","bio", "skills", "experience", "company_name",  "company_page_url")
    .eq("sent_to_llm", False)
    .order("name")
    # .limit(250)
    .execute()
)
for item in response.data:
    lead_details_list.append(item)

st.title("Dreamforce Scout App")

tab1, tab2, tab3 = st.tabs(["Scout Leads", "Scrape Details", "Find Relevant Leads"])

with tab1:
    st.title("Scout Leads")

    data_source_t1 = st.radio(
    "Choose Search Method:",
    ("None", "Use search url to search posts", "Use Keywords to search posts"),
    key="tab1_data_source"
)
    if data_source_t1 == "None":
        keywords = ""
        search_url = ""
        st.warning("Select any of the given 2 options to search the posts")
    elif data_source_t1 == "Use Keywords to search posts":
        keywords = st.text_input("Enter keywords (comma-separated):", help="#Dreamforce2025, Salesforce")
        search_url = ""
    else:
        search_url = st.text_input("Enter the search url:", help="Eg. https://www.linkedin.com/search/results/all/?keywords=%23dreamforce2025&origin=HISTORY&sid=AGZ")
        keywords = ""

    time_to_load = st.number_input("Time until scoll to load more posts (in sec):", min_value=1, max_value=1000, value=30)
    
    # Select LinkedIn account from the dropdown
    st.header("Select Linkedin Account:")
    all_status_s1 = set()
    response = (
    supabase.table("Accounts")
    .select("email_id", "password", "status")
    .execute()
)
    for leads in response.data:
        all_status_s1.add(leads['status'])

    status_input_s1 = st.selectbox("Fetch linkedin accounts by status", list(all_status_s1))
    accounts_s1 = fetch_lkd_account(status_input_s1)

    selected_username = st.selectbox("Select your LinkedIn username:", list(accounts_s1.keys()))
    password = accounts_s1.get(selected_username, None)
    if password:
        st.write(f"✅ Password for {selected_username} exists.")
    else:
        st.markdown(
            f"❌ Password for {selected_username} does <span style='color:red;'>NOT</span> exist.",
            unsafe_allow_html=True
        )

    if st.button("Execute Scout Leads"):
        results = scout_leads(time_to_load=time_to_load, username=selected_username, password=password, search_url=search_url, keywords=keywords.split(','), )
        # Ensure the CSV has a header named "LinkedIn URLs"
        if isinstance(results, list) and results and isinstance(results[0], dict):
            results_df = pd.DataFrame(results)
            if 'LinkedIn URLs' not in results_df.columns:
                results_df = results_df.rename(columns={results_df.columns[0]: 'LinkedIn URL'})
        else:
            results_df = pd.DataFrame({'LinkedIn URLs': results})
        csv = results_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Results as CSV", csv, "scout_leads_results.csv", "text/csv")



with tab2:
    st.title("Scrape Details")

    st.markdown("#### 1. Choose your data source for LinkedIn URLs")
    data_source = st.radio(
        "How would you like to provide LinkedIn profile URLs?",
        ("Use LinkedIn URLs from Supabase", "Upload CSV file"),
        key="tab2_data_source"
    )

    urls_per_account = [[] for _ in range(5)]  # Will hold URLs for each account

    if data_source == "Use LinkedIn URLs from Supabase":
        st.header("Load URLs from Database")
        num_leads = st.number_input("Total leads to load (across all accounts):", min_value=0, value=0, step=1, format="%d")
        init_range = st.number_input("Starting index:", min_value=0, value=0, step=1, format="%d")
        fin_range = num_leads + init_range - 1

        all_linkedin_urls = fetch_urls_from_all_leads(init_range=init_range, final_range=fin_range)
        if all_linkedin_urls:
            st.success(f"Found {len(all_linkedin_urls)} LinkedIn URLs in Supabase (scraped=False)")
            st.write("Sample URLs:")
            for i, url in enumerate(all_linkedin_urls[:5]):
                st.write(f"{i+1}. {url}")
            if len(all_linkedin_urls) > 5:
                st.write(f"... and {len(all_linkedin_urls) - 5} more")
        else:
            st.warning("No LinkedIn URLs found in Supabase with scraped=False")
    else:
        st.write("Upload a CSV with a column containing LinkedIn profile URLs.")
        uploaded_file = st.file_uploader("Upload CSV with LinkedIn URLs", type=["csv"])
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                st.success("CSV loaded successfully.")
            except Exception as e:
                st.error(f"Failed to read file: {e}")
                df = None
            if df is not None and not df.empty:
                def _find_url_column(df: pd.DataFrame):
                    candidates = ["linkedin url", "linkedin urls", "link", "profile_url", "profile url", "url", "profile", "profile link"]
                    for col in df.columns:
                        if str(col).strip().lower() in candidates:
                            return col
                    for col in df.columns:
                        low = str(col).strip().lower()
                        if "linkedin" in low or "link" in low or "url" in low:
                            return col
                    return None
                url_col = _find_url_column(df)
                if url_col:
                    all_linkedin_urls = df[url_col].dropna().astype(str).tolist()
                    st.success(f"Loaded {len(all_linkedin_urls)} URLs from uploaded file.")
                else:
                    st.error("Could not find a URL column. Ensure file has a column like 'LinkedIn URL', 'Link', or 'profile_url'.")
                    all_linkedin_urls = []
            else:
                all_linkedin_urls = []
        else:
            all_linkedin_urls = []

    # --- Account selection ---
    st.header("2. Select LinkedIn Accounts (up to 5)")
    all_status_s2 = set()
    response = (
        supabase.table("Accounts")
        .select("email_id", "password", "status")
        .execute()
    )
    for leads in response.data:
        all_status_s2.add(leads['status'])

    status_input_s2 = st.selectbox("Filter LinkedIn accounts by status", list(all_status_s2))
    accounts_s2 = fetch_lkd_account(status_input_s2)
    account_options = list(accounts_s2.keys())

    enforce_unique = st.checkbox("Require unique accounts for all scrapers", value=True, key="enforce_unique_accounts")

    selected_usernames = []
    for i in range(5):
        if enforce_unique:
            available_options = [acc for acc in account_options if acc not in selected_usernames]
        else:
            available_options = account_options
        selected = st.selectbox(
            f"Scraper #{i+1} LinkedIn account",
            available_options,
            key=f"multi_account_select_{i}"
        )
        selected_usernames.append(selected)

    st.markdown("**Tip:** You can assign different accounts to each scraper. If 'Require unique accounts' is checked, you can't select the same account twice.")

    # --- URL splitting logic ---
    st.header("3. Assign URLs to each account")
    st.markdown("URLs will be split evenly among the selected accounts. Each account will scrape a unique set of leads.")

    if all_linkedin_urls:
        # Split URLs as evenly as possible among accounts
        num_accounts = len([u for u in selected_usernames if u])
        if num_accounts == 0:
            st.warning("Please select at least one LinkedIn account before assigning URLs.")
        else:
            for idx, url in enumerate(all_linkedin_urls):
                urls_per_account[idx % num_accounts].append(url)
            for i, username in enumerate(selected_usernames):
                st.write(f"**Scraper #{i+1} ({username})** will process {len(urls_per_account[i])} URLs.")
                if len(urls_per_account[i]) > 0:
                    st.code("\n".join(urls_per_account[i][:3]) + ("\n..." if len(urls_per_account[i]) > 3 else ""), language="text")
    else:
        st.info("No URLs loaded yet.")

    resume_checkpoint = st.checkbox("Resume from previous checkpoint", value=True, key="resume_checkpoint")

    progress_container = st.container()

    if st.button("🚀 Start Scraping with 5 Accounts"):
        if not all_linkedin_urls:
            st.error("No LinkedIn URLs loaded. Please load URLs from Supabase or upload a CSV.")
        else:
            with progress_container:
                st.info("Starting LinkedIn profile scraping with 5 accounts. Please do not close this tab.")

                def run_scraper(idx, username, password, urls, resume_checkpoint):
                    if not password:
                        return (idx, username, None, f"Password not found for {username}. Skipping.")
                    if not urls:
                        return (idx, username, None, f"No URLs assigned to {username}. Skipping.")
                    try:
                        scraped_results = get_linkedin_profile_details(
                            urls,
                            username=username,
                            password=password,
                            resume_from_checkpoint=resume_checkpoint
                        )
                        return (idx, username, scraped_results, None)
                    except Exception as e:
                        return (idx, username, None, f"Error during scraping with {username}: {e}")

                # Prepare arguments for each scraper
                scraper_args = []
                for idx, username in enumerate(selected_usernames):
                    password = accounts_s2.get(username, None)
                    urls = urls_per_account[idx]
                    scraper_args.append((idx, username, password, urls, resume_checkpoint))

                results = []
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    futures = [executor.submit(run_scraper, *args) for args in scraper_args]
                    for future in concurrent.futures.as_completed(futures):
                        results.append(future.result())

                # Display results
                for idx, username, scraped_results, error in sorted(results, key=lambda x: x[0]):
                    st.markdown(f"### Scraper #{idx+1} ({username})")
                    if error:
                        st.error(error)
                    elif scraped_results:
                        results_df = pd.DataFrame(scraped_results)
                        st.dataframe(results_df, use_container_width=True)
                    else:
                        st.warning(f"No profiles were scraped by {username}")