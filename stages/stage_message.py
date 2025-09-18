import json
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.output_parsers import PydanticOutputParser


# Define response schema
class GeminiMessageResponse(BaseModel):
    SUBJECT: str = Field(..., description="A catchy subject line for the outreach email, within 5-7 words.")
    MESSAGE: str = Field(..., description="A personalized outreach message for the lead, within 50-70 words.")


with open("stages/wildnetEdge.txt", "r") as f:
    wildnet_edge_data = f.read()


def message_lead(lead_info: dict, api_key) -> dict:

    # Initialize the LLM
    llm = ChatGoogleGenerativeAI(
        model='models/gemini-2.5-flash',
        # google_api_key=os.getenv("GEMINI_API_KEY"),
        google_api_key=api_key,
        temperature=0.3
    )
    
    # Set up parser
    parser = PydanticOutputParser(pydantic_object=GeminiMessageResponse)
    
    # Get format instructions
    format_instructions = parser.get_format_instructions()
    
    # Create system message
    system_msg = SystemMessage(content=f"""
You are an expert lead qualifier. We (WildnetEdge) as a company offer the following services to our clients:
WildnetEdge: ```{wildnet_edge_data}```

Your task is to frame a short, crisp and highly personalised outreach message for the lead based on their profile information and our services. The message should start with a personalized greet, followed with what we can offer them in a way that it highlights the value proposition of WildnetEdge's Salesforce services and how it can benefit the lead's company. The message should be engaging and should prompt the lead to respond positively. The message should be within 50-70 words. Use the lead's first name in the message to make it more personalised. Do not mention anything about pricing or discounts in the message. The message should be professional yet friendly in tone. End the message with a call to  Here is the lead's information:

""")
    
    # Create human message with lead info and format instructions
    human_msg = HumanMessage(content=f"""
Write a message to this lead for outreach as per the above instructions.
{lead_info}

{format_instructions}
""")
    
    # Get response from LLM
    response = llm.invoke([system_msg, human_msg])
    
    # Parse the response
    parsed_output = parser.parse(response.content)

    # Calculate token sizes
    # input_tokens = 0
    # output_tokens = 0

    # # Initialize the client with API key
    # client = genai.Client(api_key=api_key)
    # genai.configure(api_key="AIzaSyCrbmArh2il2oVeOkpBxHo99hdDRRhaHIQ")

    # # Count input tokens
    # input_token = genai.count_tokens(model="gemini-2.5-flash", contents=[system_msg.content, human_msg.content]).total_token

    # # Count input tokens
    # output_token = genai.count_tokens(model="gemini-2.5-flash", contents=response.content).total_token

    # # Count input tokens (system + human messages in order)
    # input_tokens = client.models.count_tokens(
    #     model="gemini-2.5-flash",
    #     contents=[system_msg.content, human_msg.content]
    # ).total_tokens

    # # Count output tokens
    # output_tokens = client.models.count_tokens(
    #     model="gemini-2.5-flash",
    #     contents=response.content
    # ).total_tokens

    # Return as dictionary
    return {
        "lead_id": lead_info.get("lead_id"),
        "linkedin_url": lead_info.get("profile_url"),
        "name": lead_info.get("name"),
        "subject": parsed_output.SUBJECT,
        "message": parsed_output.MESSAGE
        # "input_tokens": input_tokens,
        # "output_tokens": output_tokens
    }

