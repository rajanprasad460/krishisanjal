# -*- coding: utf-8 -*-
"""
Created on Tue Jun  2 18:35:09 2026

@author: Rajan
"""

from google import genai

client = genai.Client(
    api_key="A"
)



#%%%


from dotenv import load_dotenv
import os

load_dotenv()

print(os.getenv("GEMINI_API_KEY"))