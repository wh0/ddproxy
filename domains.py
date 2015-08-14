import json
import os
import subprocess
import sys

import hammock

if len(sys.argv) != 3:
	print >> sys.stderr, 'Usage: %s zone subdomain' % sys.argv[0]
	sys.exit(1)

zone_name = sys.argv[1]
subdomain = sys.argv[2]

def config_get(key):
	return subprocess.check_output(('heroku', 'config:get',  key))[:-1]

def config_set(key, value):
	subprocess.check_output(('heroku', 'config:set', '%s=%s' % (key, value)))

cloudflare = hammock.Hammock('https://api.cloudflare.com/client/v4', headers={
	'X-Auth-Email': config_get('CLOUDFLARE_EMAIL'),
	'X-Auth-Key': config_get('CLOUDFLARE_KEY')
})
def cloudflare_result(response):
	payload = response.json()
	if not payload['success']:
		raise Exception(payload)
	return payload['result']

zones_result = cloudflare_result(cloudflare.zones.GET(params={'name': zone_name}))
if len(zones_result) == 0:
	print >> sys.stderr, 'Zone %s not found' % zone_name
	sys.exit(1)
else:
	zone_id = zones_result[0]['id']

dns_record_name = '%s.%s' % (subdomain, zone_name)
dns_records_result = cloudflare_result(cloudflare.zones(zone_id).dns_records.GET(params={'name': dns_record_name}))
if len(dns_records_result) == 0:
	print >> sys.stderr, 'DNS record %s not found. creating it' % dns_record_name
	dns_records_create_result = cloudflare_result(cloudflare.zones(zone_id).dns_records.POST(data=json.dumps({
		'type': 'A',
		'name': dns_record_name,
		'content': '0.0.0.0',
	})))
	dns_record_id = dns_records_create_result['id']
else:
	dns_record_id = dns_records_result[0]['id']

username = 'omni'
password = os.urandom(16).encode('hex')

domains = json.loads(config_get('DOMAINS') or '{}')
domains[dns_record_name] = {
	'username': username,
	'password': password,
	'zone_id': zone_id,
	'dns_record_id': dns_record_id,
}
config_set('DOMAINS', json.dumps(domains))

print 'hostname: %s' % dns_record_name
print 'username: %s' % username
print 'password: %s' % password
