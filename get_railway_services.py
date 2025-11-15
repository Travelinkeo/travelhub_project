import requests
import json

RAILWAY_TOKEN = "rw_Fe26.2**c9833887914932693024100e0ed96d80e7b5d73f2c95325bc93b4d6a5e44913d*Ekqxqs15uytVD7WSSUzTMA*Y7hkbTwE8nNVrbCaDu_gIHTv4GKTRdmVFkhGu6DSyRUKyjb5HVDlElAi5RG06xlyzxTbW7sZUOP5tnblw3zxSw*1765770514102*826cfe1bd599d72f61960fe63073fac235e8b34e94482356a7d53d9130047230*POfCl5h4KIdYZM5HjV__PAXNM3DdrcDFupV9gPYkqgQ"
PROJECT_ID = "5b8f9a05-b4cc-466b-8365-774d638b4208"

query = """
query project($id: String!) {
  project(id: $id) {
    services {
      edges {
        node {
          id
          name
        }
      }
    }
  }
}
"""

response = requests.post(
    "https://backboard.railway.com/graphql/v2",
    headers={
        "Authorization": f"Bearer {RAILWAY_TOKEN}",
        "Content-Type": "application/json"
    },
    json={
        "query": query,
        "variables": {"id": PROJECT_ID}
    }
)

print("Status:", response.status_code)
print("\nRespuesta completa:")
print(json.dumps(response.json(), indent=2))

if response.status_code == 200:
    data = response.json()
    if "data" in data and data["data"]["project"]:
        services = data["data"]["project"]["services"]["edges"]
        print("\n" + "="*60)
        print("SERVICE IDs ENCONTRADOS:")
        print("="*60)
        for service in services:
            node = service["node"]
            print(f"\nNombre: {node['name']}")
            print(f"ID: {node['id']}")
