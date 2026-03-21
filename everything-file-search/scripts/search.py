import sys
import urllib.parse
import requests
from bs4 import BeautifulSoup


def search_everything(query, base_url="http://127.0.0.1:23324"):
    params = {"s": query}
    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser', from_encoding='utf-8')
        results = []

        # Everything HTML table uses <tr> with class "trdata1" or "trdata2"
        # The file name and path are in <a> tags
        rows = soup.find_all('tr', class_=lambda x: x and x.startswith('trdata'))

        for row in rows:
            # The first <td> contains the file name and full link
            file_td = row.find('td', class_='file')
            if file_td:
                a_tag = file_td.find('a')
                if a_tag and 'href' in a_tag.attrs:
                    # href looks like "/C%3A/Users/MECHREV/..."
                    raw_href = a_tag['href']
                    # Unquote and remove leading slash
                    full_path = urllib.parse.unquote(raw_href).lstrip('/')
                    # Standardize backslashes for Windows
                    full_path = full_path.replace('/', '\\')
                    results.append(full_path)

        return results
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return []


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    if len(sys.argv) < 2:
        print("Usage: python scripts/search.py <query>")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    paths = search_everything(query)

    for path in paths:
        print(path)
