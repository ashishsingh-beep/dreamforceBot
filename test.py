import google.generativeai as genai
from langchain.schema import HumanMessage, SystemMessage

genai.configure(api_key="AIzaSyCrbmArh2il2oVeOkpBxHo99hdDRRhaHIQ")


system_msg = SystemMessage(content="""
You are an expert sales analyst. Your task is to evaluate potential leads based on the following three
                           """)
human_msg = HumanMessage(content=f"""
Evaluate this lead for potential:
Should we approach this lead? Rate potential 1-100 based on all the 3 factors (Keep the weightage in mind) and explain your reasoning based on how well they match our services. Keep the score criteria strict and give high score only to those who fulfill all the criteria to a good extent.factors:
""")

response = {'content': 'This is the dummy response'}

# input_tokens = genai.count_tokens(
#     model="gemini-1.5-flash",
#     contents=[system_msg.content, human_msg.content]
# ).total_tokens

# output_tokens = genai.count_tokens(
#     model="gemini-1.5-flash",
#     contents=[response.content]
# ).total_tokens

print(response.content)

