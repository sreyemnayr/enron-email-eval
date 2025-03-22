# NOLA-AI Programming Challenge

_Note: I opted to over-engineer this challenge with Docker containers because Mitch mentioned them in our phone conversation as a skill that was needed. Obviously, this could also be done in a more one-and-done manner using a single python module without a database._

_Also, the Yahoo Finance API doesn't go back far enough to accomodate Enron stock prices, and I couldn't find a free API that would either. I located a history of stock prices on a page from the trial._

## Sample Results

- Results CSV and zip of emails from the subset can be found in the `./results` directory
- Supplied results are from a subset of 993 emails representing up to 5 emails on every Friday.

## Running the code:

####

### 0. Prerequisites

- Docker
- Ollama (required locally on MacOS, see note to use docker for other platforms)
  - Note: on a machine which can support GPUs in docker containers (not a Mac), you can uncomment the ollama section of `docker-compose.yml`. Otherwise, make sure that ollama is running on the host and has already pulled the desired model.

### 1. Build and bring up the docker containers:

- `docker compose up -d --build`

### 2. Pull model in Ollama

- If running locally:
  - `ollama pull wizardlm2:7b`
- If running in container:
  - `docker compose exec ollama ollama pull wizardlm2:7b`

### 3. Run the app

- `docker compose run --rm app python main.py`
- Initialize databases (options e/s)
- Create a new benchmark (option n)
- Export the benchmark (option b)

## Data sources:

- Enron Email corpus is downloaded from https://www.cs.cmu.edu/~enron/
- ENE Stock Price history is from https://web.archive.org/web/20150924022158/http://www.gilardi.com/pdf/enro13ptable.pdf (I used Tabula to extract the data)

---

---

## Challenge Definition:

#### Objective:

Build a data pipeline that

- Processes a subset of the Enron email dataset, extracting key metadata.
- Retrieves historical Enron stock prices for the date of each email.
- Summarize email content using an LLM, with a flag if the email discusses stocks (see below).
- Outputs a structured CSV with the processed data.

#### Summary Guidelines:

- The summary should be structured in some way via prompt engineering so that you get the data back but also a flag set saying whether the email is about stocks or not. If the email is about stocks or the market in any form, then set a flag in the discussion column to true, otherwise that flag will be false.

#### Requirements:

- Extract the following fields from each email
  - Sender
  - Recipient
  - Date
  - Email Body (Summarized using an LLM)
  - Enron Stock Price on that Date
  - Stock Discussion Flag (True/False if the email contains stock-related terms)

#### Tools and Resources (everything should be free):

- Dataset: https://www.cs.cmu.edu/~enron/
- Use Yahoo Finance API or something similar to fetch Enron stock prices.
- Use a lightweight LLM (preferably CPU based) from Hugging Face to generate summaries.

#### Ensure the final output is a CSV file.

Submit code, desired data subset, and the final CSV via GitHub.
