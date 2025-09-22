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
        temperature=0.6
    )
    
    # Set up parser
    parser = PydanticOutputParser(pydantic_object=GeminiMessageResponse)
    
    # Get format instructions
    format_instructions = parser.get_format_instructions()
    
    # Create system message
    system_msg = SystemMessage(content=f"""
You are an expert lead qualifier. We (WildnetEdge) as a company offer the following services to our clients:
WildnetEdge: ```{wildnet_edge_data}```

Your task is to frame a crisp and highly personalised outreach message for the lead based on their profile information and our services. The message should start with a personalized greet, followed with a question if they are coming for DreamForce'2025 which will be held on 14-16 October, then in next para frame a message of what's going on in their industry in the world and how they can improve themselves, in next paragraph introduce WildnetEdge and offer/talk about some of the highly relevant salseforce services to them in a way that it highlights the value proposition of WildnetEdge's Salesforce services and how it can benefit the lead's company. The message should be engaging and should prompt the lead to respond positively. Use the lead's first name in the message to make it more personalised. Do not mention anything about pricing or discounts in the message. The message should be professional yet friendly in tone. End the message with a call to action. Here are 2 examples of good outreach messages (just for reference, do not copy them):
Example 1

Hi ABC (from Burlington County Institute of Technology),

Will you be at Dreamforce 2025 in October?

Many Education leaders are scaling student and customer impact with Salesforce. Since Burlington County Institute of Technology is driving vocational training and career readiness, I thought it would be great to connect.

At WildnetEdge, we help Marketing leaders unlock more from Salesforce CRM—enhancing insights, boosting growth, and delivering across Marketing, Sales, Service, and Education Cloud.

Would you be open to a 20-min chat during the event?

Example 2

Hi ABC (Vita Green),

Will you be at Dreamforce (Oct 14–16)? I’m excited about the shift toward the Agentic Enterprise, with AI embedded into industry-specific clouds like Healthcare.

I’d love to hear how Vita Green is streamlining customer interactions to improve service delivery and satisfaction.

At WildnetEdge, we specialize in Salesforce + AI—covering implementation, migration, app development, multi-cloud architecture, and ERP integration—to help organizations unlock the full potential of CRM.

Would you be open to a quick meet-up at Dreamforce to explore how we can accelerate growth through automation and AI?

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

