import requests
import time
from bs4 import BeautifulSoup
import os, json
from tqdm import tqdm
from argparse import ArgumentParser

def get_conference_url(venue, year):
    if venue != None and year != None:
        if check_events(venue, year):
            url = "https://aclanthology.org/events/{}-{}/".format(venue, year)
        else:
            raise NotImplementedError('Mismatch !! Check venue and year')
    else:
        raise NotImplementedError('Require venue and year')
    return url


def check_events(venue, year):
    anthology_url = 'https://aclanthology.org/'
    response = requests.get(anthology_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    events_dict = {}
    year_list = []

    tables = soup.find("main").find_all("tbody", {"class": "border-bottom"}) # [ACL Events, Non-ACL Events]
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            _venue = row.find("th").get_text().lower()
            years = row.find_all("td")
            year_list = [y.find("a")["href"].lstrip("/events/{}-".format(_venue)).rstrip('/') for y in years if y.get_text() != '']

            events_dict[_venue] = year_list

    list_of_valeus = events_dict[venue]
    if venue in events_dict.keys():
        if year in list_of_valeus:
            return True
        else:
            return False
    else:
        return False
           

def crawling(output_path, venue, year):
    conf_url = get_conference_url(venue, year)
    
    try:
        response = requests.get(conf_url)
    except:
        time.sleep(5)
        response = requests.get(conf_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    # get conf_id
    contents = soup.find("div", {"class": "card-body"}).find_all("li")
    conf_id_list = [content.find("a")["href"].replace("#", "") for content in contents]

    total_paper_info = []

    for conf_id in conf_id_list:
        paper_list = soup.find("div", id=conf_id).find_all(class_="d-sm-flex align-items-stretch")[1:] # 0번째 데이터 'Proceedings --' 제외 
        for p in tqdm(paper_list, desc=conf_id):
            parse = p.find("strong") 
            title = parse.text
            paper_url = "https://aclanthology.org" + parse.find("a")["href"]
                
            try:
                inner_page_response = requests.get(paper_url)
            except:
                time.sleep(5)
                response = requests.get(conf_url)
            inner_page_response.raise_for_status()
            inner_page = BeautifulSoup(inner_page_response.content, "html.parser")

            authors_list = []
            authors = inner_page.find("p", {"class": "lead"})

            if authors:
                authors_list = authors.find_all("a")
                authors_list = [author.get_text().strip() for author in authors_list]

            paper_details_area = inner_page.find("div", {"class": "acl-paper-details"})
            abstract_area = paper_details_area.find("div", {"class": "acl-abstract"})
            abstract = ""
            if abstract_area:
                abstract_area.find("h5").decompose()
                abstract = abstract_area.get_text().strip()
                
            items = paper_details_area.find("dl")
            paper_info = {
                        "Anthology ID": "",
                        "Year": "",
                        "Title": "",
                        "Authors": "",
                        "Abstract": "",
                        "URL": "",
                        "DOI": ""
                        }

            for item in items.find_all("dt"):
                value = item.find_next("dd")
                if value is None:
                    continue
                tag = item.get_text().strip().replace(":", "")
                value = value.get_text().strip()
                if tag == "Anthology ID":
                    paper_info[tag] = value
                elif tag == "Year":
                    paper_info[tag] = value
                elif tag == "URL":
                    paper_info[tag] = value
                elif tag == "DOI":
                    paper_info[tag] = 'http://doi.org/' + value
                    
                paper_info['Title'] = title
                paper_info['Authors'] = authors_list
                paper_info['Abstract'] = abstract

            total_paper_info.append( paper_info )

    # dump to json
    dump_json(output_path, total_paper_info)
    print("Paper details is dumped at {}".format(output_path))


def dump_json(file_path, data):
    with open(file_path, "w", encoding="utf-8", newline='') as f:
        json.dump(data, f, ensure_ascii=False, indent="\t")


def parser_config():
    """
    Argument Setting
    """
    parser = ArgumentParser(description='[ Argument ]')

    parser.add_argument("--venue", type=str, default="acl", help="Venue : acl, emnlp, conll, naacl, coling, ...")   
    parser.add_argument("--year", type=str, default="2022", help="year (yyyy)")

    return parser.parse_args()   


if __name__ == '__main__':
    args = parser_config() 

    venue = args.venue.lower()
    year = args.year

    output_dir = os.path.join('output')
    if not os.path.exists(output_dir): os.makedirs(output_dir)

    output_path = os.path.join(output_dir, "{}-{}.json".format(venue, year))
    
    crawling(output_path, venue, year)

    