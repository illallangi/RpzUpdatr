# RpzUpdatr

Updates a ConfigMap with a RPZ file for DNS based on attributes on kubernetes Services.

## Installation

    kubectl apply -f https://raw.githubusercontent.com/illallangi/RpzUpdatr/master/deploy.yaml

## Usage

Add the following attributes on a Service object:

    ddnsupdatr.illallangi.enterprises/domain: example.com

If the Service object is a Load Balancer with an IP, you're done. If not, set a CNAME to point to with `ddnsupdatr.illallangi.enterprises/cname: example.org`.

Configure your DNS server to use the ConfigMap as an RPZ zone, https://doc.powerdns.com/recursor/lua-config/rpz.html.