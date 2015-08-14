import json
import os
import traceback

import flask

import hammock

domains = json.loads(os.environ['DOMAINS'])

cloudflare = hammock.Hammock('https://api.cloudflare.com/client/v4', headers={
	'X-Auth-Email': os.environ['CLOUDFLARE_EMAIL'],
	'X-Auth-Key': os.environ['CLOUDFLARE_KEY'],
})
def cloudflare_result(response):
	payload = response.json()
	if not payload['success']:
		raise Exception(payload)
	return payload['result']

app = flask.Flask(__name__)

@app.route('/nic/update')
def update():
	if flask.request.authorization is None:
		return 'badauth', 401, {'Content-Type': 'text/plain', 'WWW-Authenticate': 'Basic realm="DynDNS API Access"'}

	if 'hostname' in flask.request.args:
		hostname = flask.request.args['hostname']
	else:
		return 'notfqdn', 200, {'Content-Type': 'text/plain'}

	if hostname in domains:
		domain = domains[hostname]
	else:
		return 'nohost', 200, {'Content-Type': 'text/plain'}

	if flask.request.authorization.username != domain['username']:
		return 'badauth', 200, {'Content-Type': 'text/plain'}
	if flask.request.authorization.password != domain['password']:
		return 'badauth', 200, {'Content-Type': 'text/plain'}

	if 'myip' in flask.request.args:
		ip = flask.request.args['myip']
	elif 'X-Forwarded-For' in flask.request.headers:
		ip = flask.request.headers['X-Forwarded-For']
	else:
		ip = flask.request.remote_addr

	try:
		dns_records_update_result = cloudflare_result(cloudflare.zones(domain['zone_id']).dns_records(domain['dns_record_id']).PUT(data=json.dumps({
			'type': 'A',
			'name': hostname,
			'content': ip,
		})))
	except:
		traceback.print_exc()
		return 'dnserr', 200, {'Content-Type': 'text/plain'}

	return 'good %s' % dns_records_update_result['content'], 200, {'Content-Type': 'text/plain'}

port = int(os.environ.get('PORT', '5000'))
app.run(host='0.0.0.0', port=port)
