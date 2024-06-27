import requests
from bs4 import BeautifulSoup
import html2text

url = 'https://www.phpunit.de/getting-started.html'

response = requests.get(url)

if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    content = soup.find('main', class_='content')
    
    h = html2text.HTML2Text()
    h.ignore_links = False
    markdown = h.handle(str(content))
    
    with open('phpunit.md', 'w', encoding='utf-8') as f:
        f.write(markdown)
        
    print('Markdown file created successfully.')