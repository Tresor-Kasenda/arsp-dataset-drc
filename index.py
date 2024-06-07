import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

def scrape_website(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # rest of your code
    
    td_elements = soup.find_all('td')
    with open('output.txt', 'w', encoding='utf-8') as f:
        for td in tqdm(td_elements, desc="Processing elements", bar_format='{l_bar}{bar:20}{r_bar}{bar:-20b}'):
            td_text = td.get_text(strip=True)
            f.write(td_text + '\n')
        print("Scraping completed and data written to output.txt")
        

# Replace 'https://www.example.com' with the URL you want to scrape
scrape_website('https://arsp.cd/registre-des-entreprises-enregistrees/')