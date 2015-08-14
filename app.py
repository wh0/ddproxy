import json
import os
import traceback

import flask

import requests

domains = json.loads(os.environ['DOMAINS'])
api_email = os.environ['CLOUDFLARE_EMAIL']
api_key = os.environ['CLOUDFLARE_KEY']

app = flask.Flask(__name__)

@app.route('/nic/update')
def update():
	if flask.request.authorization is None:
		return 'badauth', 401, {'Content-Type': 'text/plain', 'WWW-Authenticate': 'Basic realm="DynDNS API Access"'}
	if 'hostname' not in flask.request.args:
		return 'notfqdn', 200, {'Content-Type': 'text/plain'}
	hostname = flask.request.args['hostname']
	if hostname not in domains:
		return 'nohost', 200, {'Content-Type': 'text/plain'}
	domain = domains[hostname]
	if flask.request.authorization.username != domain['username']:
		return 'badauth', 200, {'Content-Type': 'text/plain'}
	if flask.request.authorization.password != domain['password']:
		return 'badauth', 200, {'Content-Type': 'text/plain'}
	ip = flask.request.remote_addr
	ip = flask.request.headers.get('X-Forwarded-For', ip)
	ip = flask.request.args.get('myip', ip)
	url = 'https://api.cloudflare.com/client/v4/zones/%s/dns_records/%s' % (
		domain['zone_identifier'],
		domain['identifier']
	)
	headers = {
		'X-Auth-Email': api_email,
		'X-Auth-Key': api_key
	}
	data = json.dumps({
		'type': 'A',
		'name': hostname,
		'content': ip
	})
	try:
		response = requests.put(url, headers=headers, data=data)
		result = response.json()
	except requests.exceptions.RequestException:
		traceback.print_exc()
		return 'dnserr', 200, {'Content-Type': 'text/plain'}
	if not result['success']:
		print response.text
		return 'dnserr', 200, {'Content-Type': 'text/plain'}
	return 'good %s' % result['result']['content'], 200, {'Content-Type': 'text/plain'}

port = int(os.environ.get('PORT', '5000'))
app.run(host='0.0.0.0', port=port)
