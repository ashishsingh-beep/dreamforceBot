import os
import streamlit as st
import pandas as pd
from stages.stage_1 import scout_leads
from stages.stage_2 import get_linkedin_profile_details
from stages.stage_3 import evaluate_lead
from stages.stage_message import message_lead
# from stages.stage_enrich import enrich_contact
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
def fetch_urls_from_all_leads(init_range, final_range, tags):
    linkedin_urls = [] 
    response = (
                supabase.table("all_leads")
                .select("linkedin_url")
                .eq("scraped", False)
                .in_("tag", tags if tags else ["dreamforce post"])  # Changed filter to in_
                .range(init_range, final_range)
                .execute()
                )
    for item in response.data:
        linkedin_urls.append(item['linkedin_url'])
    return linkedin_urls


# Load LinkedIn profile details from lead_details table for Stage 3 from Supabase
def fetch_leads_from_lead_details(limit):
    lead_details_list = [] 
    response = (
        supabase.table("lead_details")
        .select("lead_id", "name", "title", "location", "profile_url","bio", "skills", "experience", "company_name",  "company_page_url")
        .eq("sent_to_llm", False)
        .order("name")
        .limit(limit)
        .execute()
    )
    for item in response.data:
        lead_details_list.append(item)
    return lead_details_list

st.title("Dreamforce Scout App")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Scout Leads", "Scrape Details", "Find Relevant Leads", "Enrich Contacts", "Generate Personalised Messages"])

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

    st.markdown("#### Choose your data source for LinkedIn URLs")
    data_source = st.radio(
        "How would you like to provide LinkedIn profile URLs?",
        ("Use LinkedIn URLs from Supabase", "Upload CSV file"),
        key="tab2_data_source"
    )

    no_of_accounts = st.number_input("Number of LinkedIn accounts to use:", min_value=1, max_value=10, value=1, step=1, format="%d", key="no_of_accounts")
    
    tag_tab2_list = supabase.table("unique_tags").select("*").execute()
    
    tag_tab2 = st.multiselect("Filter leads by tag (optional):", [item['tag'] for item in tag_tab2_list.data if item['tag']], help="Select one or more tags to filter leads. Leave empty to fetch all tags.")
    
    urls_per_account = [[] for _ in range(no_of_accounts)]  # Will hold URLs for each account

    if data_source == "Use LinkedIn URLs from Supabase":
        st.header("1. Load URLs from Database")
        num_leads = st.number_input("Total leads to load (across all accounts):", min_value=0, value=0, step=1, format="%d")
        # init_range = st.number_input("Starting index:", min_value=0, value=0, step=1, format="%d")
        init_range = 0
        fin_range = num_leads + init_range - 1

        all_linkedin_urls = fetch_urls_from_all_leads(init_range=init_range, final_range=fin_range, tags=tag_tab2 if tag_tab2 else ['dreamforce post'])
        if all_linkedin_urls:
            st.success(f"Found {len(all_linkedin_urls)} LinkedIn URLs in Supabase (scraped=False)")
            st.write("Sample URLs:")
            for i, url in enumerate(all_linkedin_urls[:no_of_accounts]):
                st.write(f"{i+1}. {url}")
            if len(all_linkedin_urls) > no_of_accounts:
                st.write(f"... and {len(all_linkedin_urls) - no_of_accounts} more")
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
    st.header("2. Select LinkedIn Accounts")

    enforce_unique = st.checkbox("Require unique accounts for all scrapers", value=True, key="enforce_unique_accounts")

    status_inputs = []
    accounts_per_status = []
    account_options_per_status = []
    selected_usernames = []

    for i in range(no_of_accounts):
        with st.expander(f"Scraper #{i+1} Account Settings", expanded=(i == 0)):
            # Fetch all statuses for dropdown
            all_status_s2 = set()
            response = (
                supabase.table("Accounts")
                .select("email_id", "password", "status")
                .execute()
            )
            for leads in response.data:
                all_status_s2.add(leads['status'])
            status_list = list(all_status_s2)

            status_input = st.selectbox(
                f"Filter LinkedIn accounts by status for Scraper #{i+1}",
                status_list,
                key=f"status_input_s2_{i}"
            )
            status_inputs.append(status_input)

            accounts_s2 = fetch_lkd_account(status_input)
            account_options = list(accounts_s2.keys())
            account_options_per_status.append(account_options)

            # Enforce uniqueness if needed
            if enforce_unique:
                available_options = [acc for acc in account_options if acc not in selected_usernames]
            else:
                available_options = account_options

            selected = st.selectbox(
                f"Select LinkedIn account for Scraper #{i+1}",
                available_options,
                key=f"multi_account_select_{i}"
            )
            selected_usernames.append(selected)
            accounts_per_status.append(accounts_s2)

    st.markdown("**Tip:** You can assign different statuses and accounts to each scraper. If 'Require unique accounts' is checked, you can't select the same account twice.")

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

    if st.button(f"🚀 Start Scraping with {no_of_accounts} Accounts"):
        if not all_linkedin_urls:
            st.error("No LinkedIn URLs loaded. Please load URLs from Supabase or upload a CSV.")
        else:
            with st.container():
                st.info(f"Starting LinkedIn profile scraping with {no_of_accounts} accounts. Please do not close this tab.")

                def run_scraper(idx, username, password, urls):
                    if not password:
                        return (idx, username, None, f"Password not found for {username}. Skipping.")
                    if not urls:
                        return (idx, username, None, f"No URLs assigned to {username}. Skipping.")
                    try:
                        scraped_results = get_linkedin_profile_details(
                            urls,
                            username=username,
                            password=password
                        )
                        return (idx, username, scraped_results, None)
                    except Exception as e:
                        return (idx, username, None, f"Error during scraping with {username}: {e}")

                # Prepare arguments for each scraper
                scraper_args = []
                for idx, username in enumerate(selected_usernames):
                    password = accounts_per_status[idx].get(username, None)
                    urls = urls_per_account[idx]
                    scraper_args.append((idx, username, password, urls))

                results = []
                with concurrent.futures.ThreadPoolExecutor(max_workers=no_of_accounts) as executor:
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



with tab3:
    st.header("Find Relevant Leads")

    num_leads = st.number_input("Enter number of leads to Search:", key="search_leads", min_value=1)
    lead_details_list = fetch_leads_from_lead_details(num_leads)
    
    st.info(f"Found {len(lead_details_list)} leads in Supabase to process through LLM")
    if len(lead_details_list) > 0:
        st.write("Sample leads:")
        for i, lead in enumerate(lead_details_list[:3]):  # Show first 3 leads
            st.write(f"{i+1}. **{lead.get('name', 'N/A')}** - {lead.get('title', 'N/A')} at {lead.get('company_name', 'N/A')}")
        if len(lead_details_list) > 3:
            st.write(f"... and {len(lead_details_list) - 3} more")
    else:
        st.warning("No lead details found in Supabase with sent_to_llm=False")

    # --- Gemini Multi-Account Section ---
    st.subheader("Gemini API Accounts")
    num_gemini_accounts = st.number_input("Number of Gemini accounts to use:", min_value=1, max_value=10, value=1, step=1, key="num_gemini_accounts")
    gemini_api_keys = []
    for i in range(num_gemini_accounts):
        with st.expander(f"Gemini Account #{i+1} API Key", expanded=(i == 0)):
            api_key = st.text_input(f"Gemini API Key for Account #{i+1}", type="password", key=f"gemini_api_key_{i}")
            gemini_api_keys.append(api_key)

    # Distribute leads evenly among accounts
    leads_per_account = [[] for _ in range(num_gemini_accounts)]
    for idx, lead in enumerate(lead_details_list):
        leads_per_account[idx % num_gemini_accounts].append(lead)

    st.markdown("#### Sample of leads assigned to each Gemini account:")
    for i in range(num_gemini_accounts):
        with st.expander(f"Gemini Account #{i+1} Sample Leads", expanded=(i == 0)):
            leads = leads_per_account[i]
            if leads:
                for j, lead in enumerate(leads[:3]):  # Show up to 3 sample leads per account
                    st.write(f"{j+1}. **{lead.get('name', 'N/A')}** - {lead.get('title', 'N/A')} at {lead.get('company_name', 'N/A')}")
                if len(leads) > 3:
                    st.write(f"... and {len(leads) - 3} more")
            else:
                st.info("No leads assigned to this account.")

    if st.button("Execute Find Relevant Leads (Multi-Account)"):
        if any(not key for key in gemini_api_keys):
            st.error("Please provide all Gemini API Keys.")
            st.stop()
        if len(lead_details_list) == 0:
            st.error("No lead details found in Supabase.")
            st.stop()

        with st.spinner("Processing leads in series. Please wait..."):
            progress = st.progress(0)
            status = st.empty()
            results_placeholder = st.empty()
            outputs = []
            total = len(lead_details_list)
            done = 0

            for acc_idx, (api_key, leads) in enumerate(zip(gemini_api_keys, leads_per_account)):
                status.text(f"Processing leads for Gemini Account #{acc_idx+1}...")
                account_outputs = []
                for lead_info in leads:
                    try:
                        result = evaluate_lead(lead_info, api_key=api_key)
                    except Exception as e:
                        result = {
                            "lead_id": lead_info.get("lead_id"),
                            "name": lead_info.get("name"),
                            "linkedin_url": lead_info.get("profile_url"),
                            "score": 0,
                            "response": f"Error: {e}",
                            "message_generated": None,
                            "contacts_enriched": None,
                            "should_contact": None,
                            "input_tokens": 0,
                            "output_tokens": 0
                        }
                    if "lead_id" in lead_info:
                        result["lead_id"] = lead_info["lead_id"]
                    account_outputs.append(result)
                    outputs.append(result)
                    done += 1
                    progress.progress(min(done / total, 1.0))
                    status.text(f"Completed {done} out of {total} leads...")
                    try:
                        results_placeholder.dataframe(pd.DataFrame(outputs))
                    except Exception:
                        pass
                status.text(f"Finished Gemini Account #{acc_idx+1}")

            status.text("Completed all accounts.")

        # Code to update database (supabase)
        for result in outputs:
            try:
                # Insert the data in llm_response table
                supabase.table("llm_response").insert(result).execute()
                # Update the sent_to_llm column in lead_details table as True
                supabase.table("lead_details").update({"sent_to_llm": True}).eq("lead_id", result['lead_id']).execute()
            except Exception as e:
                print(f"Error inserting data: {e}")

        results_df = pd.DataFrame(outputs)
        st.dataframe(results_df)

        # CSV download
        csv_bytes = results_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download Results as CSV", csv_bytes, "evaluated_leads.csv", "text/csv")

        # Excel download
        try:
            towrite = io.BytesIO()
            with pd.ExcelWriter(towrite, engine="openpyxl") as writer:
                results_df.to_excel(writer, index=False, sheet_name="evaluated_leads")
            towrite.seek(0)
            st.download_button("Download Results as Excel", towrite.read(), "evaluated_leads.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except Exception:
            pass





with tab4:
    st.header("Enrich Contacts for Relevant Leads")

    st.info("This section is under development.")




# def fetch_leads_for_message_generate(limit):

#     # 1. Fetch llm_response where message_generated = 'no'
#     llm_responses_res = supabase.table("llm_response") \
#         .select("lead_id") \
#         .eq("message_generated", "no") \
#         .execute()
#     llm_resp_lead_id = {resp["lead_id"] for resp in (llm_responses_res.data or [])}

#     leads_to_generate_message = []
#     for lead_id in llm_resp_lead_id:
#         lead = (supabase.table("lead_details")
#                 .select("*")
#                 .eq("lead_id", lead_id)
#                 .execute()         
#         )
#         leads_to_generate_message.append(lead.data[0])
#     return leads_to_generate_message[0:limit]


def fetch_leads_for_message_generate(limit: int):
    # 1. Fetch lead_ids from llm_response where message_generated = 'no'
    llm_responses_res = (
        supabase.table("llm_response")
        .select("lead_id")
        .eq("message_generated", "no")
        .execute()
    )
    llm_resp_lead_ids = [resp["lead_id"] for resp in (llm_responses_res.data or [])]

    if not llm_resp_lead_ids:
        return []

    # 2. Fetch matching leads in one query
    leads_res = (
        supabase.table("lead_details")
        .select("*")
        .in_("lead_id", llm_resp_lead_ids)
        .limit(limit)
        .execute()
    )

    return leads_res.data or []



with tab5:
    st.header("Generate Personalised Messages for Relevant Leads")

    num_leads = st.number_input("Enter number of leads to Search:", key="search_leads_tab5", min_value=1)
    lead_details_list = fetch_leads_for_message_generate(num_leads)
    
    st.info(f"Found {len(lead_details_list)} leads in Supabase whose message is not generated")
    if len(lead_details_list) > 0:
        st.write("Sample leads:")
        for i, lead in enumerate(lead_details_list[:3]):  # Show first 3 leads
            st.write(f"{i+1}. **{lead.get('name', 'N/A')}** - {lead.get('title', 'N/A')} at {lead.get('company_name', 'N/A')}")
        if len(lead_details_list) > 3:
            st.write(f"... and {len(lead_details_list) - 3} more")
    else:
        st.warning("No lead details found in Supabase whose message is not generated.")

    # --- Gemini Multi-Account Section ---
    st.subheader("Gemini API Accounts")
    num_gemini_accounts = st.number_input("Number of Gemini accounts to use:", min_value=1, max_value=10, value=1, step=1, key="num_gemini_accounts_tab5")
    gemini_api_keys = []
    for i in range(num_gemini_accounts):
        with st.expander(f"Gemini Account #{i+1} API Key", expanded=(i == 0)):
            api_key = st.text_input(f"Gemini API Key for Account #{i+1}", type="password", key=f"gemini_api_key_tab5_{i}")
            gemini_api_keys.append(api_key)

    # Distribute leads evenly among accounts
    leads_per_account = [[] for _ in range(num_gemini_accounts)]
    for idx, lead in enumerate(lead_details_list):
        leads_per_account[idx % num_gemini_accounts].append(lead)

    st.markdown("#### Sample of leads assigned to each Gemini account:")
    for i in range(num_gemini_accounts):
        with st.expander(f"Gemini Account #{i+1} Sample Leads", expanded=(i == 0)):
            leads = leads_per_account[i]
            if leads:
                for j, lead in enumerate(leads[:3]):  # Show up to 3 sample leads per account
                    st.write(f"{j+1}. **{lead.get('name', 'N/A')}** - {lead.get('title', 'N/A')} at {lead.get('company_name', 'N/A')}")
                if len(leads) > 3:
                    st.write(f"... and {len(leads) - 3} more")
            else:
                st.info("No leads assigned to this account.")

    if st.button("Execute Generate Personalised Messages (Series)", key="execute_generate_messages_tab5"):
        if any(not key for key in gemini_api_keys):
            st.error("Please provide all Gemini API Keys.")
            st.stop()
        if len(lead_details_list) == 0:
            st.error("No lead details found in Supabase whose message is not generated.")
            st.stop()

        with st.spinner("Processing leads in series. Please wait..."):
            progress = st.progress(0)
            status = st.empty()
            results_placeholder = st.empty()
            outputs = []
            total = len(lead_details_list)
            done = 0

            # Sequential processing of accounts
            for acc_idx, (api_key, leads) in enumerate(zip(gemini_api_keys, leads_per_account)):
                status.text(f"Processing leads for Gemini Account #{acc_idx+1}...")
                for lead_info in leads:
                    try:
                        result = message_lead(lead_info, api_key=api_key)
                    except Exception as e:
                        result = {
                            "lead_id": lead_info.get("lead_id"),
                            "linkedin_url": lead_info.get("profile_url"),
                            "name": lead_info.get("name"),
                            "subject": "",
                            "message": f"Error: {e}"
                        }
                    if "lead_id" in lead_info:
                        result["lead_id"] = lead_info["lead_id"]
                    outputs.append(result)
                    done += 1
                    progress.progress(min(done / total, 1.0))
                    status.text(f"Completed {done} out of {total} leads...")
                    try:
                        # Display the result immediately after processing
                        results_placeholder.dataframe(pd.DataFrame(outputs))
                    except Exception:
                        st.error("Error displaying results.")
                status.text(f"Finished Gemini Account #{acc_idx+1}")

            status.text("Completed all accounts.")

        # Code to update database (supabase)
        for result in outputs:
            try:
                # Insert the data in message table
                supabase.table("message").insert(result).execute()
                # Update the message_generated column in llm_response table as True
                supabase.table("llm_response").update({"message_generated": 'yes'}).eq("lead_id", result['lead_id']).execute()
            except Exception as e:
                st.error(f"Error inserting/updating data for lead_id {result.get('lead_id')}: {e}")

        results_df = pd.DataFrame(outputs)
        st.dataframe(results_df)

        # CSV download
        csv_bytes = results_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download Results as CSV", csv_bytes, "message.csv", "text/csv", key="download_csv_tab5")

        # Excel download
        try:
            towrite = io.BytesIO()
            with pd.ExcelWriter(towrite, engine="openpyxl") as writer:
                results_df.to_excel(writer, index=False, sheet_name="message")
            towrite.seek(0)
            st.download_button("Download Results as Excel", towrite.read(), "message.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="download_excel_tab5")
        except Exception:
            st.error("Error generating Excel file.")