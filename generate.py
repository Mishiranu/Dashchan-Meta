#!/usr/bin/env python3

import base64
import hashlib
import json
import os
import requests
import subprocess
import sys
import zipfile

class ManifestEntry:
	def __init__(self, element, attributes):
		self.element = element
		self.attributes = attributes

	def get(self, key):
		return self.attributes.get(key)

class Apk:
	def __init__(self, title, manifest_entries, fingerprints, length, sha256sum):
		self.title = title
		self.manifest_entries = manifest_entries
		self.fingerprints = fingerprints
		self.length = length
		self.sha256sum = sha256sum

class Package:
	def __init__(self, title, extension, version_name, version_code,
		min_sdk, length, source, source_legacy, fingerprint, sha256sum):
		self.title = title
		self.extension = extension
		self.version_name = version_name
		self.version_code = version_code
		self.min_sdk = min_sdk
		self.length = length
		self.source = source
		self.source_legacy = source_legacy
		self.fingerprint = fingerprint
		self.sha256sum = sha256sum

class Extension:
	def __init__(self, etype, title):
		self.etype = etype
		self.title = title
		self.packages = []

os.chdir(os.path.dirname(sys.argv[0]))
os.chdir('update')
with open('source.json') as file:
    source_config = json.load(file)

def dumpapk(path):
	length = os.path.getsize(path)
	m = hashlib.sha256()
	with open(path, 'rb') as file:
		m.update(file.read())
	sha256sum = ':'.join('{:02X}'.format(x) for x in m.digest())
	manifest_entries = []

	output = subprocess.run(['aapt', 'd', 'badging', path],
		capture_output = True).stdout.decode('utf-8')
	title = None
	for line in output.split('\n'):
		if line.startswith('application-label:'):
			line = line[18:]
			if line[0] == '\'':
				line = line[1:-1]
			title = line
	if title.startswith('Dashchan for '):
		title = title[13:]
	elif title.startswith('Dashchan '):
		title = title[9:]

	output = subprocess.run(['aapt', 'd', 'xmltree', path, 'AndroidManifest.xml'],
		capture_output = True).stdout.decode('utf-8')
	element = None
	attributes = None
	for line in output.split('\n'):
		line = line.strip()
		if line.startswith('E: '):
			if element:
				manifest_entries.append(ManifestEntry(element, attributes))
			element = line[3:]
			index = element.find(' (')
			if index >= 0:
				element = element[:index]
			attributes = {}
		elif line.startswith('A: '):
			line = line[3:]
			index = line.find('=')
			if index >= 0:
				key = line[:index]
				value = line[index + 1:]
				index = key.find('(')
				if index >= 0:
					key = key[:index]
				if key.startswith('android:'):
					key = key[8:]
				index = value.find(' (Raw: ')
				if index >= 0:
					value = value[index + 7:-1]
				if value[0] == '"':
					value = value[1:-1]
				if value.startswith('(type'):
					index = value.find(')')
					if index >= 0:
						value = value[index + 1:]
					if value.startswith('0x'):
						value = int(value, 16)
				attributes[key] = value
	if element:
		manifest_entries.append(ManifestEntry(element, attributes))
	
	fingerprints = []
	with zipfile.ZipFile(path, 'r') as zip:
		for name in zip.namelist():
			if name.startswith('META-INF/') and name.endswith('.RSA'):
				with zip.open(name) as cert_entry:
					cert = cert_entry.read()
				output = subprocess.run(['openssl', 'pkcs7', '-inform', 'DER', '-print_certs'],
					input = cert, capture_output = True).stdout.decode('utf-8')
				b64 = None
				for line in output.split('\n'):
					if line == '-----BEGIN CERTIFICATE-----':
						b64 = ''
					elif line == '-----END CERTIFICATE-----':
						m = hashlib.sha256()
						m.update(base64.b64decode(b64))
						fingerprint = ':'.join('{:02X}'.format(x) for x in m.digest())
						fingerprints.append(fingerprint)
						b64 = None
					elif b64 is not None:
						b64 += line
	return Apk(title, manifest_entries, fingerprints, length, sha256sum)

client_title = ''
clients = []
extensions = {}

def addpackage(apk, title, source, source_legacy):
	package_title = None
	is_chan = False
	is_library = False
	name = None
	version_name = None
	version_code = None
	min_sdk = None
	fingerprint = None

	for entry in apk.manifest_entries:
		if entry.element == 'manifest':
			version_name = entry.get('versionName')
			version_code = entry.get('versionCode')
		elif entry.element == 'uses-sdk':
			min_sdk = entry.get('minSdkVersion')
		elif entry.element == 'uses-feature':
			feature_name = entry.get('name')
			is_chan = feature_name == 'chan.extension'
			is_library = feature_name == 'lib.extension'
		elif entry.element == 'meta-data':
			metadata_name = entry.get('name')
			if is_chan and metadata_name == 'chan.extension.name':
				name = entry.get('value')
			elif is_library and metadata_name == 'lib.extension.name':
				name = entry.get('value')
			elif is_chan and metadata_name == 'chan.extension.title':
				package_title = entry.get('value')
			elif is_library and metadata_name == 'lib.extension.title':
				package_title = entry.get('value')
	if package_title is None:
		package_title = apk.title
	if len(apk.fingerprints) == 1:
		fingerprint = apk.fingerprints[0]

	if version_name and version_code and min_sdk and fingerprint:
		if is_chan or is_library or name:
			if (is_chan or is_library) and name:
				if title.lower().startswith(name):
					title = title[len(name):]
				extension = extensions.get(name)
				if extension is None:
					etype = ''
					if is_chan:
						etype = 'chan'
					elif is_library:
						etype = 'library'
					extension = Extension(etype, package_title)
					extensions[name] = extension
				elif title == '':
					extension.title = package_title
				extension.packages.append(Package(title, name, version_name, version_code, min_sdk,
					apk.length, source, source_legacy, fingerprint, apk.sha256sum))
		else:
			global client_title
			if len(client_title) == 0 or title == '':
				client_title = package_title
			clients.append(Package(title, 'client', version_name, version_code, min_sdk,
				apk.length, source, source_legacy, fingerprint, apk.sha256sum))

client_url = source_config.get('client_url')
if client_url:
	m = hashlib.sha1()
	m.update(client_url.encode())
	name = ''.join('{:02x}'.format(x) for x in m.digest()) + '.apk'
	path = '/tmp/' + name
	if not os.path.exists(path) or os.path.getsize(path) == 0:
		with open(path, 'wb') as file:
		 	file.write(requests.get(client_url, allow_redirects = True).content)
	index = client_url.find('://')
	if index >= 0:
		client_url = client_url[index + 1:]
	addpackage(dumpapk(path), '', client_url, client_url)

relative_url_legacy = source_config['relative_url_legacy']
for f in os.listdir('package'):
	if f.endswith('.apk'):
		title = f[:-4]
		if title.startswith('Dashchan'):
			title = title[8:]
		source = os.path.join('package', f)
		source_legacy = relative_url_legacy + source
		addpackage(dumpapk(source), title, source, source_legacy)

json_dict = {}
json_v1_dict = {}
repository = source_config.get('repository')
if repository:
	json_dict['meta'] = {'repository': repository}
	json_v1_dict['title'] = repository
applications_v1 = []
if len(clients) > 0 or len(extensions) > 0:
	json_v1_dict['applications'] = applications_v1

if len(clients) > 0:
	packages = []
	packages_v1 = []
	json_dict['client'] = packages
	applications_v1.append({
		'name': 'client',
		'type': 'client',
		'title': client_title,
		'packages': packages_v1
	})
	clients.sort(key = lambda package: package.title)
	for package in clients:
		title = 'Release'
		if len(package.title):
			title = package.title
		packages.append({
			'title': title,
			'name': package.version_name,
			'code': package.version_code,
			'minVersion': 1,
			'maxVersion': 1,
			'minSdk': package.min_sdk,
			'length': package.length,
			'source': package.source_legacy,
			'fingerprint': package.fingerprint
		})
		packages_v1.append({
			'title': title,
			'version_name': package.version_name,
			'version_code': package.version_code,
			'min_api_version': 1,
			'max_api_version': 1,
			'min_sdk': package.min_sdk,
			'length': package.length,
			'source': package.source,
			'fingerprint': package.fingerprint,
			'sha256sum': package.sha256sum
		})

for name in sorted(extensions):
	extension = extensions[name]
	extension.packages.sort(key = lambda package: package.title)
	packages = []
	packages_v1 = []
	json_dict[name] = packages
	applications_v1.append({
		'name': name,
		'type': extension.etype,
		'title': extension.title,
		'packages': packages_v1
	})
	for package in extension.packages:
		title = 'Release'
		if len(package.title):
			title = package.title
		packages.append({
			'title': title,
			'name': package.version_name,
			'code': package.version_code,
			'version': 1,
			'minSdk': package.min_sdk,
			'length': package.length,
			'source': package.source_legacy,
			'fingerprint': package.fingerprint
		})
		packages_v1.append({
			'title': title,
			'version_name': package.version_name,
			'version_code': package.version_code,
			'api_version': 1,
			'min_sdk': package.min_sdk,
			'length': package.length,
			'source': package.source,
			'fingerprint': package.fingerprint,
			'sha256sum': package.sha256sum
		})

with open('data.json', 'w') as file:
	file.write(json.dumps(json_dict, indent = '\t'))
	file.write('\n')
with open('data-v1.json', 'w') as file:
	file.write(json.dumps(json_v1_dict, indent = '\t'))
	file.write('\n')
