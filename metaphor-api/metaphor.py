import datetime
import os
import yake

from dotenv import load_dotenv
from metaphor_python import Metaphor
from collections import defaultdict
from flask import Flask, request, jsonify

app = Flask(__name__)

# load the Metaphor API key from .env file
load_dotenv()
METAPHOR_API_KEY = os.getenv('METAPHOR_API_KEY')

@app.route("/", methods=["GET"])
def home():
    return "Welcome to the Flask app!"

@app.route("/search", methods=["GET"])
def search():
    try:
        user_query = request.args.get("query")
        if not user_query:
            return jsonify({"error": "No query provided"}), 400
        
        
        metaphor = Metaphor(api_key=METAPHOR_API_KEY)

        # grab the most relevant results
        # Metaphor API will return results that are within one year of the publish date
        today = datetime.date.today()
        one_year_ago = today - datetime.timedelta(days=365)

        # Metaphor API call
        response = metaphor.search(user_query, num_results=10, 
                                include_domains=["scholar.google.com", "jstor.org", "ncbi.nlm.nih.gov", "springer.com", "ieeexplore.ieee.org", "sciencedirect.com", "onlinelibrary.wiley.com", "nature.com", "pnas.org", "arxiv.org", "frontiersin.org", "dl.acm.org"],
                                start_crawl_date=str(one_year_ago), 
                                use_autoprompt=True,)

        # create a hashmap to store
        # key = article title
        # value = article id, keywords YAKE, article url
        document_id_dict = defaultdict(str)
        keyword_dict = defaultdict(list)
        url_dict = defaultdict(str)

        for result in response.results:
            #print(result.title, result.url, result.id)
            #print()

            document_id_dict[result.title] = result.id
            keywords = get_keywords(str(document_id_dict[result.title]), metaphor)
            keyword_dict[result.title] = keywords
            url_dict[result.title] = result.url
        
        #print(url_dict)

        #print(list(url_dict.values())[0])
        search_results = sorted(list(document_id_dict.keys()))
        similar_papers = sorted(get_similar_papers(list(url_dict.values())[0], metaphor))

        print("**************Returning results...**************")
        return jsonify({
            "search_results": search_results,
            "similar_papers": similar_papers,
            "keywords": keyword_dict
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

def get_similar_papers(document_url, metaphor):
    """
    function takes in two arguments: the URL of the research paper and the metaphor API object

    Returns a list of URLs in which their similarity is most relevant to the search phrase
    """
    # grab the most relevant results
    # Metaphor API will return results that are within one year of the publish date
    today = datetime.date.today()
    one_year_ago = today - datetime.timedelta(days=365)

    # Metaphor API call
    response = metaphor.find_similar(str(document_url), num_results=10, 
                            include_domains=["scholar.google.com", "jstor.org", "ncbi.nlm.nih.gov", "springer.com", "ieeexplore.ieee.org", "sciencedirect.com", "onlinelibrary.wiley.com", "nature.com", "pnas.org", "arxiv.org", "frontiersin.org", "dl.acm.org"],
                            start_crawl_date=str(one_year_ago),)
    
    similar_urls_lst = []
    for result in response.results:
        similar_urls_lst.append(result.url)
    #print("SIMILAR PAPERS: " + str(similar_urls_lst))
    return similar_urls_lst

def get_keywords(document_id, metaphor):
    """
    Uses the Yet Another Keyword Extractor (YAKE) Python library to extract the most important keywords of a provided text input

    function takes in two arguments: the document id provided by the Metaphor API and the Metaphor API object

    Returns a list of most relevant keywords as calculated by YAKE
    """

    # Metaphor API call
    response = metaphor.get_contents(document_id)
    text = response.contents[0].extract

    # YAKE custom settings
    language = "en"
    max_ngram_size = 3
    deduplication_thresold = 0.9
    deduplication_algo = 'seqm'
    windowSize = 1
    numOfKeywords = 10

    # YAKE keyword extractor
    kw_extractor = yake.KeywordExtractor(lan=language, 
                                    n=max_ngram_size, 
                                    dedupLim=deduplication_thresold, 
                                    dedupFunc=deduplication_algo, 
                                    windowsSize=windowSize, 
                                    top=numOfKeywords)
                                            
    keywords = kw_extractor.extract_keywords(text)

    # list to store the keywords
    keywords_lst = []
    for kw, score in keywords:
        if kw not in ["div", "Download PDF", "pdf", "Download", "href"]:
            keywords_lst.append(kw)

    #print(important_words)
    return keywords_lst


if __name__ == '__main__':
    app.run(debug=True)
