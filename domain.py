import re

websites = []

with open('company_domains.txt', 'r', encoding='utf-8') as file:
    lines = file.readlines()
    for line in lines:
        # Extract the domain from the line using regular expression
        match = re.search(r'(?:[a-z]+\.[a-z]+)$', line)
        if match:
            domain = match.group()
            websites.append(domain)

# Store the domains in a file called "domains.txt"
with open('domains.txt', 'w', encoding='utf-8') as file:
    for domain in websites:
        file.write(domain + '\n')


# read domains.txt and remove all duplication
with open('domains.txt', 'r', encoding='utf-8') as file:
    lines = file.readlines()
    domains = set()
    for line in lines:
        domains.add(line.strip())
        
# Store the unique domains in a file called "unique_domains.txt"
with open('unique_domains.txt', 'w', encoding='utf-8') as file:
    for domain in domains:
        file.write(domain + '\n')
        print(domain)
        
# Read company_domains.txt and domains.txt
with open('company_domains.txt', 'r', encoding='utf-8') as company_file, open('domains.txt', 'r', encoding='utf-8') as domains_file:
    company_domains = company_file.readlines()
    existing_domains = domains_file.readlines()

# Find the domains that the company doesn't have in domains.txt
new_domains = [domain for domain in company_domains if domain not in existing_domains]

# Store the new domains in a file called "new_domains.txt"
with open('new_domains.txt', 'w', encoding='utf-8') as new_file:
    for domain in new_domains:
        new_file.write(domain)

