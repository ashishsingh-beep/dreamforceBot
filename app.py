import os
import streamlit as st
import pandas as pd
from stages.stage_1 import scout_leads
from stages.stage_2 import get_linkedin_profile_details
from stages.stage_3 import evaluate_lead
import io
from supabase import create_client, Client
from dotenv import load_dotenv


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


    
    # Data source selection
    data_source = st.radio(
        "Choose data source:",
        ("Use LinkedIn URLs from Supabase", "Upload CSV file"),
        key="tab2_data_source"
    )
    
    if data_source == "Use LinkedIn URLs from Supabase":

        # Load Data from Supabase:
        st.header("Load URLs from Database")
        num_leads = st.number_input("Enter Total leads to load:", min_value=0, value=0, step=1, format="%d")
        init_range = st.number_input("Enter Starting index", min_value=0, value=0, step=1, format="%d")
        fin_range = num_leads+init_range - 1

        linkedin_urls = fetch_urls_from_all_leads(init_range=init_range, final_range=fin_range)
        if len(linkedin_urls):
            st.info(f"Found {len(linkedin_urls)} LinkedIn URLs in Supabase (scraped=False)")
        if len(linkedin_urls) > 0:
            st.write("Sample URLs:")
            for i, url in enumerate(linkedin_urls[:5]):  # Show first 5 URLs
                st.write(f"{i+1}. {url}")
            if len(linkedin_urls) > 5:
                st.write(f"... and {len(linkedin_urls) - 5} more")
        else:
            st.warning("No LinkedIn URLs found in Supabase with scraped=False")
    else:
        st.write("Upload a CSV with a column containing LinkedIn profile URLs.")
        uploaded_file = st.file_uploader("Upload CSV with LinkedIn URLs", type=["csv"])


    # Select LinkedIn account from the dropdown (fetched from supabase)
    st.header("Select Linkedin Account:")
    all_status_s2 = set()
    response = (
    supabase.table("Accounts")
    .select("email_id", "password", "status")
    .execute()
)
    for leads in response.data:
        all_status_s2.add(leads['status'])

    status_input_s2 = st.selectbox("Fetch linkedin accounts by status (s2)", list(all_status_s2))
    accounts_s2 = fetch_lkd_account(status_input_s2)

    selected_username_s2 = st.selectbox("Select your LinkedIn username (s2)", list(accounts_s2.keys()))
    password_s2 = accounts_s2.get(selected_username_s2, None)
    if password_s2:
        st.write(f"✅ Password for {selected_username_s2} exists.")
    else:
        st.markdown(
            f"❌ Password for {selected_username_s2} does <span style='color:red;'>NOT</span> exist.",
            unsafe_allow_html=True
        )

    # Resume from checkpoint option
    resume_checkpoint = st.checkbox("Resume from previous checkpoint", value=True, key="resume_checkpoint")
    
    # Progress tracking placeholders
    progress_container = st.container()
    
    def _find_url_column(df: pd.DataFrame):
        candidates = ["linkedin url", "linkedin urls", "link", "profile_url", "profile url", "url", "profile", "profile link"]
        for col in df.columns:
            if str(col).strip().lower() in candidates:
                return col
        # fuzzy: look for column that contains 'linkedin' or 'link' or 'url'
        for col in df.columns:
            low = str(col).strip().lower()
            if "linkedin" in low or "link" in low or "url" in low:
                return col
        return None

    if st.button("Execute Scrape Details"):
        urls = []
        
        if data_source == "Use LinkedIn URLs from Supabase":
            if len(linkedin_urls) == 0:
                st.error("No LinkedIn URLs found in Supabase.")
            else:
                urls = linkedin_urls
        else:
            if uploaded_file is None:
                st.error("Please upload a CSV file.")
            else:
                try:
                    df = pd.read_csv(uploaded_file)
                except Exception as e:
                    st.error(f"Failed to read file: {e}")
                else:
                    if df.empty:
                        st.error("Uploaded file is empty.")
                    else:
                        url_col = _find_url_column(df)
                        if not url_col:
                            st.error("Could not find a URL column. Ensure file has a column like 'LinkedIn URL', 'Link', or 'profile_url'.")
                        else:
                            urls = df[url_col].dropna().astype(str).tolist()
                            if not urls:
                                st.error("No URLs found in the detected column.")

        if urls:
            with progress_container:
                # Progress indicators
                st.info("🚀 Starting LinkedIn profile scraping...")
                st.warning("⚠️ **Important**: Do NOT close this browser tab while scraping is in progress. The scraper will save progress automatically.")
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                scraped_count = st.empty()
                current_profile = st.empty()
                results_preview = st.empty()
                
                # Real-time results container
                results_container = st.container()
                
                try:
                    # Initialize progress tracking
                    status_text.text("Initializing scraper...")
                    
                    # Import the updated scraping function
                    from stages.stage_2 import get_linkedin_profile_details
                    
                    # Start scraping with progress callback
                    results = []
                    total_urls = len(urls)
                    
                    # Check for existing progress
                    import os
                    import json
                    progress_file = 'scraping_progress.json'
                    
                    if resume_checkpoint and os.path.exists(progress_file):
                        try:
                            with open(progress_file, 'r') as f:
                                saved_progress = json.load(f)
                            existing_results = saved_progress.get('scraped_data', [])
                            start_index = saved_progress.get('current_index', 0)
                            
                            if existing_results:
                                st.success(f"📂 Resumed from checkpoint: {len(existing_results)} profiles already scraped")
                                results.extend(existing_results)
                        except Exception as e:
                            st.warning(f"Could not load checkpoint: {e}")
                    
                    # Call the scraping function
                    status_text.text("🔍 Scraping LinkedIn profiles...")
                    scraped_results = get_linkedin_profile_details(
                        urls, 
                        username=selected_username_s2 or None, 
                        password=password_s2 or None,
                        resume_from_checkpoint=resume_checkpoint
                    )
                    
                    # Update final results
                    if scraped_results:
                        results = scraped_results
                        
                        # Update progress indicators
                        progress_bar.progress(1.0)
                        status_text.text("✅ Scraping completed successfully!")
                        scraped_count.success(f"🎉 Successfully scraped {len(results)} profiles")
                        
                        # Process and save to database
                        saved_count = 0
                        failed_count = 0
                        
                        for result in results:
                            try:
                                # Insert the data in lead_details table
                                response = (
                                    supabase.table("lead_details")
                                    .insert(result)
                                    .execute()
                                )
                                
                                # Update the scraped column in all_leads table as True
                                response = (
                                    supabase.table("all_leads")
                                    .update({"scraped": True})
                                    .eq("lead_id", result['lead_id'])
                                    .execute()
                                )
                                saved_count += 1
                                
                            except Exception as e:
                                failed_count += 1
                                st.error(f"Error saving profile {result.get('name', 'Unknown')}: {e}")
                        
                        # Show database save results
                        if saved_count > 0:
                            st.success(f"💾 Saved {saved_count} profiles to database")
                        if failed_count > 0:
                            st.warning(f"⚠️ Failed to save {failed_count} profiles to database")
                        
                        # Display results
                        results_df = pd.DataFrame(results)
                        st.subheader("📊 Scraped Profile Details")
                        st.dataframe(results_df, use_container_width=True)
                        
                        # Download options
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            csv = results_df.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                "📄 Download as CSV", 
                                csv, 
                                "linkedin_profile_details.csv", 
                                "text/csv",
                                use_container_width=True
                            )
                        
                        with col2:
                            # Excel download
                            try:
                                import io
                                towrite = io.BytesIO()
                                with pd.ExcelWriter(towrite, engine="openpyxl") as writer:
                                    results_df.to_excel(writer, index=False, sheet_name="LinkedIn_Profiles")
                                towrite.seek(0)
                                st.download_button(
                                    "📊 Download as Excel", 
                                    towrite.read(), 
                                    "linkedin_profile_details.xlsx", 
                                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    use_container_width=True
                                )
                            except Exception:
                                st.info("Excel download unavailable (missing openpyxl)")
                        
                        # Clean up progress file
                        try:
                            if os.path.exists(progress_file):
                                os.remove(progress_file)
                        except:
                            pass
                            
                    else:
                        status_text.text("❌ No profiles were scraped")
                        st.warning("⚠️ No profiles were returned from the scraper. This could be due to:")
                        st.write("- Network issues")
                        st.write("- LinkedIn blocking/rate limiting")
                        st.write("- Invalid URLs")
                        st.write("- Authentication problems")
                        
                        # Check if partial results exist
                        if os.path.exists(progress_file):
                            try:
                                with open(progress_file, 'r') as f:
                                    saved_progress = json.load(f)
                                partial_results = saved_progress.get('scraped_data', [])
                                
                                if partial_results:
                                    st.info(f"📂 Found {len(partial_results)} partially scraped profiles")
                                    if st.button("Load Partial Results"):
                                        results_df = pd.DataFrame(partial_results)
                                        st.dataframe(results_df)
                                        csv = results_df.to_csv(index=False).encode('utf-8')
                                        st.download_button("Download Partial Results", csv, "partial_linkedin_profiles.csv", "text/csv")
                            except:
                                pass
                
                except KeyboardInterrupt:
                    st.warning("🛑 Scraping was interrupted by user")
                    status_text.text("Scraping stopped by user")
                    
                except Exception as e:
                    st.error(f"❌ Error during scraping: {e}")
                    status_text.text(f"Error: {str(e)}")
                    
                    # Check for partial results on error
                    progress_file = 'scraping_progress.json'
                    if os.path.exists(progress_file):
                        try:
                            with open(progress_file, 'r') as f:
                                saved_progress = json.load(f)
                            partial_results = saved_progress.get('scraped_data', [])
                            
                            if partial_results:
                                st.info(f"📂 Recovered {len(partial_results)} profiles from progress file")
                                results_df = pd.DataFrame(partial_results)
                                st.dataframe(results_df)
                                csv = results_df.to_csv(index=False).encode('utf-8')
                                st.download_button("Download Recovered Results", csv, "recovered_linkedin_profiles.csv", "text/csv")
                        except:
                            pass
    
    # Show existing progress if available
    progress_file = 'scraping_progress.json'
    if os.path.exists(progress_file):
        try:
            with open(progress_file, 'r') as f:
                saved_progress = json.load(f)
            
            scraped_count = len(saved_progress.get('scraped_data', []))
            current_idx = saved_progress.get('current_index', 0)
            total_count = saved_progress.get('total_urls', 0)
            
            if scraped_count > 0:
                st.info(f"📁 **Progress File Found**: {scraped_count} profiles scraped, stopped at index {current_idx}/{total_count}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔄 Clear Progress File", key="clear_progress"):
                        try:
                            os.remove(progress_file)
                            st.success("Progress file cleared!")
                            st.experimental_rerun()
                        except:
                            st.error("Failed to clear progress file")
                
                with col2:
                    if st.button("👀 Preview Saved Progress", key="preview_progress"):
                        partial_results = saved_progress.get('scraped_data', [])
                        if partial_results:
                            st.dataframe(pd.DataFrame(partial_results))
        except:
            pass



with tab3:
    st.header("Find Relevant Leads")
    
    st.info(f"Found {len(lead_details_list)} leads in Supabase (sent_to_llm=False)")
    if len(lead_details_list) > 0:
        st.write("Sample leads:")
        for i, lead in enumerate(lead_details_list[:3]):  # Show first 3 leads
            st.write(f"{i+1}. **{lead.get('name', 'N/A')}** - {lead.get('title', 'N/A')} at {lead.get('company_name', 'N/A')}")
        if len(lead_details_list) > 3:
            st.write(f"... and {len(lead_details_list) - 3} more")
    else:
        st.warning("No lead details found in Supabase with sent_to_llm=False")
    
    gemini_api_key = st.text_input("Gemini API Key", type="password")

    if st.button("Execute Find Relevant Leads"):
        if not gemini_api_key:
            st.error("Please provide Gemini API Key.")
            st.stop()
            
        if len(lead_details_list) == 0:
            st.error("No lead details found in Supabase.")
        else:
            # Convert Supabase data to the format expected by evaluate_lead
            leads_to_process = []
            for lead in lead_details_list:
                lead_info = {
                    "name": str(lead.get("name", "")).strip(),
                    "title": str(lead.get("title", "")).strip(),
                    "location": str(lead.get("location", "")).strip(),
                    "profile_url": str(lead.get("profile_url", "")).strip(),
                    "bio": str(lead.get("bio", "")).strip(),
                    "experience": str(lead.get("experience", "")).strip(),
                    "lead_id": lead.get("lead_id"),  # Keep lead_id for reference
                    "company_name": str(lead.get("company_name")).strip(),
                    "company_page_url": str(lead.get("company_page_url")).strip(),
                    "sent_to_llm": lead.get('sent_to_llm')
                }
                leads_to_process.append(lead_info)

            if leads_to_process:
                total = len(leads_to_process)
                progress = st.progress(0)
                status = st.empty()
                results_placeholder = st.empty()

                outputs = []
                for idx, lead_info in enumerate(leads_to_process):
                    status.text(f"Processing {idx+1}/{total}...")

                    try:
                        result = evaluate_lead(lead_info, api_key=gemini_api_key)
                    except Exception as e:
                        result = {
                            "lead_id": lead_info.get("lead_id"),
                            "name": lead_info.get("name"),
                            "linkedin_url": lead_info.get("profile_url"),
                            "score": 0,
                            "response": f"Error: {e}",
                            "should_contact": None,
                            "input_tokens": 0,
                            "output_tokens": 0
                        }

                    # Add lead_id if available (from Supabase data)
                    if "lead_id" in lead_info:
                        result["lead_id"] = lead_info["lead_id"]

                    outputs.append(result)

                    # update UI
                    try:
                        results_placeholder.dataframe(pd.DataFrame(outputs))
                    except Exception:
                        pass

                    progress.progress((idx + 1) / total)

                status.text("Completed.")


                # Code to update database (supabase)

                for result in outputs:
                    try:
                        # Insert the data in lead_details table
                        response = (
                        supabase.table("llm_response")
                        .insert(result)
                        .execute()
                    )
                        # Update the scraped column in lead_details table as True
                        response = (
                            supabase.table("lead_details")
                            .update({"sent_to_llm": True})
                            .eq("lead_id", result['lead_id'])
                            .execute()
                    )
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
                    # fallback: disable excel button silently if engine missing
                    pass