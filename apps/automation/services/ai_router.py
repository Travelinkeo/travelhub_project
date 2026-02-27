import os
import logging
from enum import Enum
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal

import google.generativeai as genai
import instructor
from pydantic import BaseModel, Field, validator

# Configure Logging
logger = logging.getLogger(__name__)

# --- 1. Data Models (The "Truth") ---

class EmailType(str, Enum):
    TICKET_ISSUANCE = "ticket_issuance"
    SCHEDULE_CHANGE = "schedule_change"
    QUOTE_REQUEST = "quote_request"
    MARKETING = "marketing"
    OTHER = "other"

class FlightSegment(BaseModel):
    airline_code: str = Field(..., description="2-letter IATA code (e.g., LA, AV, CM)")
    flight_number: str = Field(..., description="Flight number without airline code")
    origin: str = Field(..., min_length=3, max_length=3, description="3-letter IATA airport code")
    destination: str = Field(..., min_length=3, max_length=3, description="3-letter IATA airport code")
    departure_date: datetime
    arrival_date: Optional[datetime] = None

class TicketSchema(BaseModel):
    pnr: str = Field(..., min_length=6, max_length=6, description="6-character alphanumeric PNR/Record Locator")
    ticket_number: Optional[str] = Field(None, description="13-digit ticket number if available")
    passenger_name: str = Field(..., description="Full passenger name")
    itinerary: List[FlightSegment]
    total_amount: Optional[Decimal] = Field(None, description="Total cost found in the ticket")
    currency: Optional[str] = Field("USD", description="Currency code (USD, VES, etc.)")
    issuing_agency: Optional[str] = None

# --- 2. The Router (Gemini Logic) ---

class GeminiRouter:
    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY not found in environment variables.")
            raise ValueError("GEMINI_API_KEY is missing")
        
        genai.configure(api_key=api_key)
        
        # Initialize Instructor client
        # Note: Instructor wraps the generative model to force Pydantic outputs
        self.client = instructor.from_gemini(
            client=genai.GenerativeModel("gemini-2.5-flash"),
            mode=instructor.Mode.GEMINI_JSON,
        )

    def classify_email(self, content: str) -> EmailType:
        """
        Determines the category of the email content.
        """
        try:
            category = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": f"Classify this email content into one of the following categories: {', '.join([e.value for e in EmailType])}.\n\nEmail Content:\n{content[:5000]}"
                    }
                ],
                response_model=EmailType,
            )
            return category
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            return EmailType.OTHER

    def extract_ticket_data(self, content: str) -> Optional[TicketSchema]:
        """
        Extracts structured ticket data from the content.
        """
        try:
            ticket_data = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": f"Extract the flight ticket information from the following text matches the schema exactly.\n\nText:\n{content[:15000]}"
                    }
                ],
                response_model=TicketSchema,
            )
            return ticket_data
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return None

# --- 3. The Validator (Sanitizer) ---
# Placeholder for now - will verify PNRs against DB later
def validate_ticket(ticket: TicketSchema) -> bool:
    if not ticket:
        return False
    # Example logic: PNR must be 6 chars (already handled by Pydantic)
    # Future: Check Duplicate PNR in DB
    return True
