from aisysprojserver_clienttools.admin import AdminClient
import sys
import json

env, user = sys.argv[1:]

client = AdminClient('https://aisysproj.kwarc.info')

result = client.new_user(env, user)
with open('/tmp/' + env + '.json', 'w') as f:
    json.dump(result, f, indent=2)

