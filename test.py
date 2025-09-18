# import google.generativeai as genai
# from langchain.schema import HumanMessage, SystemMessage

# genai.configure(api_key="AIzaSyCrbmArh2il2oVeOkpBxHo99hdDRRhaHIQ")


# system_msg = SystemMessage(content="""
# You are an expert sales analyst. Your task is to evaluate potential leads based on the following three
#                            """)
# human_msg = HumanMessage(content=f"""
# Evaluate this lead for potential:
# Should we approach this lead? Rate potential 1-100 based on all the 3 factors (Keep the weightage in mind) and explain your reasoning based on how well they match our services. Keep the score criteria strict and give high score only to those who fulfill all the criteria to a good extent.factors:
# """)

# response = {'content': 'This is the dummy response'}

# # input_tokens = genai.count_tokens(
# #     model="gemini-1.5-flash",
# #     contents=[system_msg.content, human_msg.content]
# # ).total_tokens

# # output_tokens = genai.count_tokens(
# #     model="gemini-1.5-flash",
# #     contents=[response.content]
# # ).total_tokens

# print(response.content)


# a = [{'a':1, 'b':2, 'c':3}, {'a':4, 'b':5, 'c':6}, {'a':7, 'b':8, 'c':9}, {'a':10, 'b':11, 'c':12}]

# b = [1, 3, 5, 7, 9]

# print([item for item in a if item['a'] in b])


import os
from supabase import create_client, Client
from dotenv import load_dotenv
load_dotenv()

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)


def fetch_leads_for_message_generate(limit):

    # 1. Fetch llm_response where message_generated = 'no'
    llm_responses_res = supabase.table("llm_response") \
        .select("lead_id") \
        .eq("message_generated", "no") \
        .execute()
    llm_resp_lead_id = {resp["lead_id"] for resp in (llm_responses_res.data or [])}

    leads_to_generate_message = []
    for lead_id in llm_resp_lead_id:
        lead = (supabase.table("lead_details")
                .select("*")
                .eq("lead_id", lead_id)
                .execute()         
        )
        leads_to_generate_message.append(lead.data[0])
    return leads_to_generate_message

print(fetch_leads_for_message_generate(1)[0])
print(type(fetch_leads_for_message_generate(1)[0]))




# print(len(llm_resp_lead_id))
# print(len(lead_details_lead_id))


