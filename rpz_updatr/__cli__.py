#!/usr/bin/env python

DOMAIN_ANNOTATION = "ddnsupdatr.illallangi.enterprises/domain"
CNAME_ANNOTATION = "ddnsupdatr.illallangi.enterprises/cname"

import datetime
import kubernetes
import os
import sys
import time 
import textwrap
import jinja2

def main():
  starttime=time.time()
  timeout = float(os.environ.get("UPDATE_INTERVAL", 15))
  while True: 
    rpzUpdate()
    sleep = max(0, timeout - ((time.time() - starttime) % timeout))
    if sleep > 1:
      print('{0}    Sleeping {1:00.0f} seconds'.format(datetime.datetime.now().isoformat(), sleep), flush=True)
      time.sleep(sleep)

def rpzUpdate():
  try:
    if 'KUBERNETES_SERVICE_HOST' in os.environ:
      kubernetes.config.load_incluster_config()
    else:
      kubernetes.config.load_kube_config()
  except kubernetes.config.ConfigException as e:
    exit("Cannot initialize kubernetes API, terminating.")
      
  a_records = {}
  ptr_records = {}
  cname_records = {}
  v1 = kubernetes.client.CoreV1Api()
  services = v1.list_service_for_all_namespaces(watch=False)
  for svc in services.items:
    if svc is not None and svc.metadata is not None and svc.metadata.annotations is not None and DOMAIN_ANNOTATION in svc.metadata.annotations:
      print("{0}    Processing service {2} in namespace {1}: ".format(datetime.datetime.now().isoformat(), svc.metadata.namespace, svc.metadata.name), flush=True)
      if CNAME_ANNOTATION in svc.metadata.annotations:
        print("{0}     - {1} CNAME {2}".format(datetime.datetime.now().isoformat(), svc.metadata.annotations.get(DOMAIN_ANNOTATION), svc.metadata.annotations.get(CNAME_ANNOTATION)), flush=True)
        if svc.metadata.annotations.get(DOMAIN_ANNOTATION) not in cname_records:
          cname_records[svc.metadata.annotations.get(DOMAIN_ANNOTATION)] = svc.metadata.annotations.get(CNAME_ANNOTATION)
      elif svc.status is not None and svc.status.load_balancer is not None and svc.status.load_balancer.ingress is not None:
        for ingress in svc.status.load_balancer.ingress:
          if ingress.ip is not None:
            print("{0}     - {1} A {2}".format(datetime.datetime.now().isoformat(), svc.metadata.annotations.get(DOMAIN_ANNOTATION), ingress.ip), flush=True)
            print("{0}     - {2} PTR {1}".format(datetime.datetime.now().isoformat(), svc.metadata.annotations.get(DOMAIN_ANNOTATION), ingress.ip), flush=True)
            if svc.metadata.annotations.get(DOMAIN_ANNOTATION) not in a_records:
              a_records[svc.metadata.annotations.get(DOMAIN_ANNOTATION)] = ingress.ip
            if ingress.ip not in ptr_records:
              ptr_records[ingress.ip] = svc.metadata.annotations.get(DOMAIN_ANNOTATION)

  print("{0}    Rendering {1} records into {2} zone: ".format(datetime.datetime.now().isoformat(), len(a_records) + len(ptr_records), os.environ.get("ZONE_ORIGIN", "rpz.local")), end='', flush=True)
  environment = jinja2.Environment(loader=jinja2.FileSystemLoader('templates'), trim_blocks=True)
  template = environment.get_template('zone.j2')
  body = template.render(
    origin=os.environ.get("ZONE_ORIGIN", "rpz.local"),
    nameserver="ns.local",
    email="nsadmin@local",
    serial=1,
    refresh=3600,
    retry=600,
    expire=604800,
    ttl=1800,
    a_records=a_records,
    ptr_records=ptr_records,
    cname_records=cname_records)
  print("Rendered {0} bytes".format(len(body)))
  print("{0}    Updating configmap {1} in {2} namespace: ".format(datetime.datetime.now().isoformat(), os.environ.get("ZONE_CONFIGMAP"), os.environ.get("ZONE_NAMESPACE")), end='', flush=True)
  api_response = v1.read_namespaced_config_map(os.environ.get("ZONE_CONFIGMAP"), os.environ.get("ZONE_NAMESPACE"))
  if api_response.data is None:
    api_response.data = {}
  if api_response.data.get(os.environ.get("ZONE_KEY")) == body:
    print("No change required")
  else:
    api_response.data[os.environ.get("ZONE_KEY")] = body
    try: 
      api_response = v1.patch_namespaced_config_map(os.environ.get("ZONE_CONFIGMAP"), os.environ.get("ZONE_NAMESPACE"), api_response, pretty=False)
      print("Updated")
    except kubernetes.client.rest.ApiException as e:
      print("Exception when calling CoreV1Api->patch_namespaced_config_map: %s\n" % e)
    print(textwrap.indent(body, "{0}      ".format(datetime.datetime.now().isoformat())), end='')

if __name__ == "__main__":
  main()