Role Name
=========

letsencrypt-dns01 - create some SSL certs using the ACME dns-01 method

Requirements
------------

ACME in general is a challenge-response protocol - you talk to the
servers with an CSR in hand and they give you a challenge string (not
actually a nonce, since it gets reused) to put somewhere.

In the case of DNS-01, you put it in the DNS, in the form of a TXT
record, generally alongside the A or AAAA record for the particular
host which you're genning up the certs for.  Therefore, you need a DNS
server which will accept TSIG-signed UPDATE messages for the various
zones which you propose to host the servers in.

The full manual of arms for accomplishing this is out of scope for this README,
but here are a couple of links and a clue:

https://technotes.seastrom.com/2014/11/06/genning-up-tsig-keys-for-dns-update-messages.html

https://technotes.seastrom.com/2014/11/06/updating-zones-with-tsig-part-2.html

You're probably eventually going to want to wildcard a zone.  Try this
in your named.conf (it's good practice to put generation dates in your
tsig key name):

zone "vpn.example.com" {
        type master ;
        file "master/rs/vpn.example.com-dynamic" ;
        update-policy {
                grant "vpn.example.com-20190205-00" wildcard *.vpn.example.com A AAAA TXT ;

        } ;
} ;



Role Variables
--------------

This role will bomb out if you don't set a bunch of variables before starting.

The usual ClueTrust methodology is to set default values in playbook_dir/group_vars/all.yml

You can override them per host with files in playbook_dir/host_vars/inventory_hostname.yml

In addition to other variables, you should set these there:

host_specific_files: "{{ inventory_dir }}/host_files/{{ inventory_hostname }}"

which_ca: acme-staging.api.letsencrypt.org
# which_ca: acme-v02.api.letsencrypt.org

cert_emailaddress: sslcert@example.com

nsupdate_hmac: hmac-sha256
nsupdate_key_name: vpn.example.com-20190205-00
nsupdate_key_secret: base64-nsupdate-key-secret==
nsupdate_server: ns.example.com


Note that while you can overwrite which nameserver you're talking to
for which host in your ansible inventory (as well as the key secrets
and such), some kind of multidimensional SAN cert dystopia where
individual hosts need to update domains that are hosted on more than
one nameserver with more than one key was considered to be a bridge
too far.  Sorry, this role doesn't do that.


Dependencies
------------

None

Example Playbook
----------------

Including an example of how to use your role (for instance, with variables passed in as parameters) is always nice for users too:

- hosts: vpnservers
  gather_facts: no
  tasks:
    - include_role:
        name: letsencrypt-dns01


Once you've run this role, you will be rewarded with a series of files
(with traditional-ish names) in
play_dir/host_files/hostname.vpn.example.org/crypto/

[root@ansible ~/workdir]# ls -l host_files/hostname.vpn.example.org/crypto/
total 33
-rw-r--r-- 1 root root 3566 Feb  6 20:25 server-fullchain.crt
-rw-r--r-- 1 root root 1679 Feb  6 20:25 server-intermediate.crt
-rw-r--r-- 1 root root 1887 Feb  6 20:25 server.crt
-rw-r--r-- 1 root root 1033 Feb  6 20:25 server.csr
-rw------- 1 root root 1704 Feb  6 20:25 server.key
[root@ansible ~/workdir]# 



License
-------

BSD

Author Information
------------------

rs@seastrom.com


