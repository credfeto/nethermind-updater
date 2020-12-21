import os
import pathlib
from urllib.request import Request, urlopen

from python_graphql_client import GraphqlClient

root = pathlib.Path(__file__).parent.resolve()
client = GraphqlClient(endpoint="https://api.github.com/graphql")


TOKEN = os.environ.get("SOURCE_PUSH_TOKEN", "")
GITHUB_ENV = os.environ.get("GITHUB_ENV", "")
CURRENT_VERSION = os.environ.get("CURRENT_VERSION", "")


def make_query():
    return """
query {
  repository(owner:"NethermindEth", name:"nethermind") {
    releases(first:20, orderBy: {direction:DESC, field: CREATED_AT}) {
      nodes {
        name
        createdAt
        isDraft
        isPrerelease
        publishedAt
        releaseAssets(last:20) {
          nodes {
            name
            downloadUrl
            size
            createdAt
            contentType
          }
        }    
      }
    }    
  }
}
"""


def fetch_releases(oauth_token):
    releases = []

    data = client.execute(
        query=make_query(),
        headers={"Authorization": "Bearer {}".format(oauth_token)},
    )

    for release in data["data"]["repository"]["releases"]["nodes"]:
        if release["isDraft"]:
            continue

        if release["isPrerelease"]:
            continue

        release_name = release["name"][1:]
        print(release_name)

        for artifact in release["releaseAssets"]["nodes"]:
            artifact_name = artifact["name"]
            if not artifact_name.startswith("nethermind-windows-amd64-"):
                continue
            if not artifact_name.endswith(".zip"):
                continue

            artifact_download_url = artifact["downloadUrl"]
            print(artifact_name)
            print(artifact_download_url)

            releases.append({"name": release_name, "artifact_name": artifact_name, "download": artifact_download_url})

    return releases


def download(release):
    name = release["name"]
    url = release["download"]

    package_filename = "nethermind.windows-amd64." + release["name"] + ".zip"

    filename = root / package_filename

    if filename.exists():
        print("Skipping " + name + " as it already exists")
        return filename

    request = Request(url)
    request.add_header('Accepts', 'application/octet-stream')

    print("Requesting " + name + "...")
    response = urlopen(request, timeout=600)

    print(" - Downloading...")
    content = response.read()

    print(" - Downloaded " + package_filename)
    filename.open("wb").write(content)

    return filename


def set_github_env(version, filename):
    if GITHUB_ENV == "":
        print("No GITHUB_ENV defined")
        return

    f = open(GITHUB_ENV, "a")
    f.write("DOWNLOADED_VERSION=" + version + "\r\n")
    f.write("DOWNLOADED_FILE=" + filename + "\r\n")
    f.close()


def update():
    print("==================================================================")
    print("Updating ")
    print(TOKEN[::-1])
    print("==================================================================")

    releases = fetch_releases(TOKEN)

    print(releases)

    for release in releases:
        version = release["name"]
        if CURRENT_VERSION != "" or version > CURRENT_VERSION:
            filename = download(release)

            set_github_env(version, filename)
            break

    print("Completed")
    

if __name__ == "__main__":
    update()
