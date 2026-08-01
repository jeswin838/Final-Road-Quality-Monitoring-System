import urllib.request
import json

try:
    req = urllib.request.Request('http://localhost:5000/api/alerts')
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print(f'Total markers: {len(data)}')
        
        for r in data:
            lat_str = str(r.get('latitude'))
            lon_str = str(r.get('longitude'))
            
            # This is how JS parseFloat works (roughly)
            url = f'http://localhost:5000/api/location-reports?lat={lat_str}&lon={lon_str}'
            req2 = urllib.request.Request(url)
            try:
                with urllib.request.urlopen(req2) as res2:
                    reports = json.loads(res2.read().decode())
                    if not reports:
                        print(f'Warning: 0 reports for {r.get("id")} at {lat_str}, {lon_str}')
            except urllib.error.HTTPError as e:
                print(f'HTTP Error on {r.get("id")}: {e.code} for URL {url}')
                print(e.read().decode())
except Exception as e:
    print('Global Error:', e)
