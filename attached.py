import os
import time
from googlesearch import search
from urllib.parse import urlparse

# Read company names from the file
with open('sorted.txt', 'r', encoding='utf-8') as file:
    company_names = file.readlines()

def extract_domain(url):
    """
    Extracts the domain from a given URL.

    Args:
        url (str): The URL from which to extract the domain.

    Returns:
        str: The domain extracted from the URL.
    """
    domain = urlparse(url).netloc
    return domain

# Perform Google search and get domain names
results = []
for company in company_names:
    company = company.strip()
    if not company:
        continue
    try:
        print(f"Searching for {company}...")
        search_results = list(search(company, num=1, stop=1))
        if search_results:
            domain = extract_domain(search_results[0])
            print(domain)
            # write the results to a file
            results.append(f"{company} - {domain}")
        else:
            results.append(f"{company} - No domain found")
    except Exception as e:
        results.append(f"{company} - Error: {e}")

# Write results to a file
with open('company_domains.txt', 'w', encoding='utf-8') as output_file:
    for result in results:
        output_file.write(result + '\n')
