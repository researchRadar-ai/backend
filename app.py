# app.py

from flask import Flask, request, jsonify
import pysondb

app = Flask(__name__)


# setup
papers = pysondb.db.getDb("data/papers")
projects = pysondb.db.getDb("data/projects")
projPapers = pysondb.db.getDb("data/project_papers")


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
