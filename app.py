# app.py

from flask import Flask, request, jsonify
import pysondb
from metaphor_python import Metaphor
import requests

# from recommendersystem import inference
import xml.etree.ElementTree as ET

app = Flask(__name__)


# setup
papers = pysondb.db.getDb("data/papers")
projects = pysondb.db.getDb("data/projects")
projPapers = pysondb.db.getDb("data/project_papers")


METAPHOR_API_KEY = "2c14596c-15cd-42e6-b969-d4717a6f60ee"
metaphor = Metaphor(api_key=METAPHOR_API_KEY)


@app.get("/api/hello")
def hello_world():
    return jsonify({"message": "f;;lkj;000;lkfjsalfd, World!"})


@app.route("/api/project/new", methods=["POST"])
def create_project():
    # Get JSON data from the request
    data = request.get_json()
    project = {
        "name": data["name"],
        "papers": [],
    }
    pid = projects.add(project)  # returns id

    return jsonify({"project_id": str(pid)})


@app.route("/api/project/list_projects", methods=["GET"])
def list_projects():
    resp = projects.getAll()
    for proj in resp:
        proj["id"] = str(proj["id"])
        del proj["papers"]
    return jsonify(resp)


@app.route("/api/project/list_papers", methods=["POST"])
def list_papers():
    data = request.get_json()

    print(data)

    proj_papers = projPapers.getByQuery({"project_id": int(data["project_id"])})

    if data["type"] == "saved":
        proj_papers = list(
            filter(lambda x: x["saved"] == True & x["read"] == True, proj_papers)
        )
    elif data["type"] == "toread":
        new = []
        for paper in proj_papers:
            if paper["saved"] == True and paper["read"] == False:
                new.append(paper)
        proj_papers = new
    elif data["type"] == "recommend":
        # sort prod_paper by rating descending
        proj_papers = sorted(proj_papers, key=lambda x: x["rating"], reverse=True)[:10]

    # reformat and get paper data
    output = []

    for paper in proj_papers:
        paper_data = papers.getByQuery({"paper_id": paper["paper_id"]})[0]

        del paper_data["paper_id"]
        del paper_data["citations"]
        paper_data["journal"] = "Unknown"
        paper_data["authors"] = ", ".join(paper_data["authors"])

        print(paper["read"], paper["saved"])

        output.append(paper_data)

    return jsonify(output)


def extract_arxiv_id(url):
    end = url.split("/")[-1].split(".")
    try:
        return end[0] + "." + end[1]
    except:
        return end[0]


def get_semantic_scholar_info(arxiv_id):
    base_url = "https://api.semanticscholar.org/v1/paper/arXiv:"

    # Fetch data from Semantic Scholar
    response = requests.get(base_url + arxiv_id)
    data = response.json()

    # Return citation count and impact score
    # Note: Semantic Scholar doesn't have a generic "impact score", but citations can be a metric of impact.
    return len(data.get("citations", []))


def get_paper_base_data(paper_id):
    base_url = "http://export.arxiv.org/api/query?"
    query = "id_list=" + paper_id

    # Send a GET request to the arXiv API
    response = requests.get(base_url + query)

    # Raise an exception if the request was unsuccessful
    response.raise_for_status()

    # Parse the XML response
    root = ET.fromstring(response.text)

    # Extract information from XML
    ns = {"default": "http://www.w3.org/2005/Atom"}
    entry = root.find("default:entry", ns)

    title = entry.find("default:title", ns).text.strip()
    authors = [
        author.find("default:name", ns).text
        for author in entry.findall("default:author", ns)
    ]
    abstract = entry.find("default:summary", ns).text.strip()
    year = entry.find("default:published", ns).text.split("-")[0]

    # Return the extracted information in the desired format
    return {
        "paper_id": paper_id,
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "year": year,
        "citations": get_semantic_scholar_info(paper_id),
    }


def add_paper_to_project(project_id, paper_id):  # paper_id is arxiv id
    project_paper = {
        "project_id": project_id,
        "paper_id": paper_id,
        "rating": 1,
        "annotations": {},
        "engagement": {
            "click_count": 0,
            "view_duration": 0,
        },
        "saved": False,
        "read": False,
    }
    id = projPapers.add(project_paper)

    old_papers = projects.getById(project_id)["papers"]
    old_papers.append(id)

    projects.updateById(project_id, {"papers": old_papers})


@app.route("/api/engagement/update", methods=["POST"])
def update_engagement():
    metric, value, project_id, paper_id = (
        request.get_json()["metric"],
        request.get_json()["value"],
        request.get_json()["project_id"],
        request.get_json()["paper_id"],
    )
    db_paper_id = projPapers.getByQuery(
        {"paper_id": paper_id, "project_id": project_id}
    )[0]["id"]

    if metric == "click":
        upd_engagement = projPapers.getById(db_paper_id)["engagement"]
        upd_engagement["click_count"] += 1
        projPapers.updateById(db_paper_id, {"engagement": upd_engagement})
    elif metric == "view":
        upd_engagement = projPapers.getById(db_paper_id)["engagement"]
        upd_engagement["view_duration"] += value
        projPapers.updateById(db_paper_id, {"engagement": upd_engagement})
    elif metric == "read":
        projPapers.updateById(db_paper_id, {"read": value})
    elif metric == "save":
        projPapers.updateById(db_paper_id, {"saved": value})

    # update ML
    # await inference.update_model(user, paper)
    # currently running in a loop in the background


@app.route("/api/search", methods=["GET"])
def search():
    user_query = request.args.get("query")
    project_id = request.args.get("project_id")
    print(request.args)
    # if not user_query:
    #     return jsonify({"error": "No query provided"}), 400

    response = metaphor.search(
        user_query,
        num_results=10,
        include_domains=["arxiv.org"],
        # start_crawl_date=str(one_year_ago),
        use_autoprompt=True,
    )

    ids = [extract_arxiv_id(r.url) for r in response.results]
    output = []

    for paper in ids:
        try:
            if papers.getByQuery({"paper_id": paper}) == []:
                papers.add(get_paper_base_data(paper))
            add_paper_to_project(int(project_id), paper)  # todo change to project id

            paper_data = papers.getByQuery({"paper_id": paper})[0]

            del paper_data["paper_id"]
            del paper_data["citations"]
            paper_data["journal"] = "Unknown"
            paper_data["authors"] = ", ".join(paper_data["authors"])

            # print(paper['read'], paper['saved'])
        except Exception:
            continue

        output.append(paper_data)

    return jsonify(output)
