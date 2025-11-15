import requests
import sys

RAILWAY_TOKEN = "rw_Fe26.2**c9833887914932693024100e0ed96d80e7b5d73f2c95325bc93b4d6a5e44913d*Ekqxqs15uytVD7WSSUzTMA*Y7hkbTwE8nNVrbCaDu_gIHTv4GKTRdmVFkhGu6DSyRUKyjb5HVDlElAi5RG06xlyzxTbW7sZUOP5tnblw3zxSw*1765770514102*826cfe1bd599d72f61960fe63073fac235e8b34e94482356a7d53d9130047230*POfCl5h4KIdYZM5HjV__PAXNM3DdrcDFupV9gPYkqgQ"
PROJECT_ID = "5b8f9a05-b4cc-466b-8365-774d638b4208"
ENVIRONMENT_ID = "e901c076-8984-425e-bf2a-a5c3bf8c2ec1"

SERVICES = {
    "web": "946cf527-4f75-4a05-afd5-0e936d6bd5e0",
    "worker": "22b49d88-906d-46a1-9256-455dcb00c545",
    "beat": "357beeac-7e16-4cba-b1df-c05ab95a42a7"
}

def toggle_service(service_id, sleep):
    if sleep:
        # Apagar servicio
        query = """
        mutation serviceInstanceUpdate($environmentId: String!, $serviceId: String!) {
          serviceInstanceUpdate(environmentId: $environmentId, serviceId: $serviceId, input: {sleepApplication: true})
        }
        """
    else:
        # Encender servicio
        query = """
        mutation serviceInstanceUpdate($environmentId: String!, $serviceId: String!) {
          serviceInstanceUpdate(environmentId: $environmentId, serviceId: $serviceId, input: {sleepApplication: false})
        }
        """
    
    variables = {
        "environmentId": ENVIRONMENT_ID,
        "serviceId": service_id
    }
    
    response = requests.post(
        "https://backboard.railway.com/graphql/v2",
        headers={
            "Authorization": f"Bearer {RAILWAY_TOKEN}",
            "Content-Type": "application/json"
        },
        json={"query": query, "variables": variables}
    )
    
    if response.status_code != 200:
        print(f"    Error {response.status_code}: {response.text}")
        return False
    
    data = response.json()
    if "errors" in data:
        print(f"    GraphQL Error: {data['errors']}")
        return False
    
    return True

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    
    if action == "stop":
        print("Apagando servicios...")
        for name, service_id in SERVICES.items():
            if toggle_service(service_id, sleep=True):
                print(f"  OK {name} apagado")
            else:
                print(f"  FAIL {name}")
    
    elif action == "start":
        print("Encendiendo servicios...")
        for name, service_id in SERVICES.items():
            if toggle_service(service_id, sleep=False):
                print(f"  OK {name} encendido")
            else:
                print(f"  FAIL {name}")
    
    else:
        print("Uso: python railway_toggle.py [start|stop]")
