###hyperfast augmented reality editing for quick wedding planning/budgeting with event hooks for vendor outreach and supply purchasing

ideated + built in 37 minutes at cursor toronto in july

"build a wedding planning tool to help out couples who are doing it themselves"

1. ingests claude chat data from both partners being wed as big jsons
2. uses a BERT classifier algorithm to isolate significant life details and interests into a smaller json
3. gemini turns the smaller json into a set of system prompts
4. system prompts go into an open source augmented reality + genai model (sub 3s latency)
5. voice commands to alter the environment (i.e. add balloons, change outfits, etc)
6. voice commands also utilize playwright to add supplies to your amazon cart automatically
7. voice commands also use resend to automatically reach out to nearby vendors via resend + maps api
