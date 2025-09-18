import json
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.output_parsers import PydanticOutputParser
import google.generativeai as genai   


# Load environment variables
load_dotenv()

# Define response schema
class GeminiScoreResponse(BaseModel):
    SCORE: int = Field(..., description="Lead score between 0 and 100")
    RESPONSE: str = Field(..., description="Reasoning for the score. Write within the range of 50-100 words.")
    SHOULD_CONTACT: int = Field(..., description="1 if lead should be contacted, else 0")

# # Load services data (you'll need to adjust the path)
# with open("stages/services.json", "r") as f:
#     services_data = json.load(f)
with open("stages/wildnetEdge.txt", "r") as f:
    wildnet_edge_data = f.read()

def evaluate_lead(lead_info: dict, api_key) -> dict:
    """
    Evaluate a lead using Gemini 2.5 Flash and return structured output.
    
    Args:
        lead_info (dict): Dictionary containing lead information
        
    Returns:
        dict: Dictionary with SCORE, RESPONSE, and SHOULD_CONTACT keys
    """
    # Initialize the LLM
    llm = ChatGoogleGenerativeAI(
        model='models/gemini-2.5-flash',
        # google_api_key=os.getenv("GEMINI_API_KEY"),
        google_api_key=api_key,
        temperature=0.3
    )
    
    # Set up parser
    parser = PydanticOutputParser(pydantic_object=GeminiScoreResponse)
    
    # Get format instructions
    format_instructions = parser.get_format_instructions()
    
    # Create system message
    system_msg = SystemMessage(content=f"""
You are an expert lead qualifier. We (WildnetEdge) as a company offer the following services to our clients:
WildnetEdge: ```{wildnet_edge_data}```

Your task is to evaluate each lead's potential whether they are a potential buyer of our (wildnetEdge's) salesforce service or whether they are potential seller of salesforce services like us (WildnetEdge). Refer following points to identify if they are a potential buyer and score on that basis:
Score the lead on a scale of 1-100 based on crieteria 1 and 2 and then multiply with a multiplier based on criteria 3 to get the final score:
Criteria - 1: The lead must be at the position of some authority like Manager, Sr. Manager, Director, Head, VP, C-suites, founder, etc. not at employee level (like Developer, Analyst, etc.). Give extra points and mention explicitly if they are in IT Department but only if they are among mentioned positions. (High weightage)
Criteria - 2: The COMPANY at which the lead is working MUST not offer IT or software services like WildnetEdge. In other words the industry of their company must not fall under "IT or software service" or any services that are mentioned above within triple backticks i.e. their company should not be our direct competitior or ours. Aditionally and VERY IMPORTANTLY, their company should not be a partner or reseller of Salesforce like us. Note: Your your intelligence and provided context about lead to evaluate what their company does, in case if you can't find out what their company does, just mention it in your response and give the score between 40-60 given 1st point is satisfied i.e. lead is at one of the mentioned position in company. Don't make any assumption (Very High Weightage)
Criteria - 3: This criteria is based on lead's location. After scoring based on above two criteria, apply following multiplier to the score:
- If lead's location is in USA, Canada, UK, Germany, Italy, France, Netherlands, Switzerland, Sweden, Ireland, Australia, Singapore - multiply the score by 1
- If lead's location is in India, UAE, Saudi Arabia, Israel, Qatar, Egypt - multiply the score by 0.8
- If lead's location is in any other country - multiply the score by 0.5
For ex. if lead scores 70 based on first two criteria and is located in USA, final score will be 70*1=70, if lead is located in India, final score will be 70*0.8=56 and if lead is located in any other country, final score will be 70*0.5=35.
""")
    
    # Create human message with lead info and format instructions
    human_msg = HumanMessage(content=f"""
Evaluate this lead for potential:
{lead_info}

Should we approach this lead? Score the leads based on above rule (0-100) and explain your reasoning and lead's location based on how well they match our services. Keep the score criteria strict and give high score only to those who fulfill all the criteria to a good extent.

{format_instructions}
""")
    
    # Get response from LLM
    response = llm.invoke([system_msg, human_msg])
    
    # Parse the response
    parsed_output = parser.parse(response.content)


    # Set contacts_enriched and message_generated based on score
    if parsed_output.SCORE >= 50:
        contacts_enriched = 'no'
        message_generated = 'no'
    elif parsed_output.SCORE < 50:
        contacts_enriched = 'ineligible'
        message_generated = 'ineligible'
    else:
        contacts_enriched = None
        message_generated = None

    # Calculate token sizes
    input_tokens = 0
    output_tokens = 0

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
        "name": lead_info.get("name"),
        "linkedin_url": lead_info.get("profile_url"),
        "location": lead_info.get("location"),
        "score": parsed_output.SCORE,
        "response": parsed_output.RESPONSE,
        "should_contact": parsed_output.SHOULD_CONTACT,
        "contacts_enriched": contacts_enriched,
        "message_generated": message_generated,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens
    }


# # Example usage:
# if __name__ == "__main__":
#     # Example lead data
#     sample_lead = {
#     "name": "Mariyappan Sivathanu",
#     "bio": "Salesforce CRM Specialist | Freelancer | 7 X Salesforce Certification | Specialized in Financial, Banking, Healthcare, & Non-Profit Services.\nSenior Salesforce Developer/Consultant | Driving Scalable, Industry-Specific Salesforce Solutions\n\nAs a Senior Salesforce Developer/Consultant at GeekSoft Consulting, I specialize in delivering impactful Salesforce CRM implementations that drive digital transformation and operational agility for enterprise clients. With deep expertise in Salesforce Health Cloud and a strong foundation across non-profit fund development and banking sectors, I craft tailored, scalable solutions aligned with each client’s unique business needs.\n\nI bring a blend of technical proficiency and strategic insight, consistently leading end-to-end Salesforce projects from architecture to deployment while enhancing system efficiency, user engagement, and long-term value. My approach integrates best practices with industry specific knowledge to empower organizations in achieving meaningful outcomes.",
#     "skills": "['Freelance\\nFreelance', 'Business-to-Business (B2B)\\nBusiness-to-Business (B2B)']",
#     "experience": "Founder - Salesforce Specialist ...",
#     "company_page_url": "https://www.linkedin.com/company/108029464/",
#     "profile_url": "https://www.linkedin.com/in/ACoAAA4iA5oBf9yWnEw6NypczgDxjeHMkcTbdbk"
#     }
    
#     try:
#         result = evaluate_lead(sample_lead,"AIzaSyCrbmArh2il2oVeOkpBxHo99hdDRRhaHIQ")
#         print(json.dumps(result, indent=2))
#     except Exception as e:
#         print(f"Error: {e}")
