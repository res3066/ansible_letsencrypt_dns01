letsencrypt-dns01
=========

Create some SSL certs using the ACME dns-01 method

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

- [Genning up tsig keys for dns update messages](https://technotes.seastrom.com/2014/11/06/genning-up-tsig-keys-for-dns-update-messages.html)
- [Updating zones with tsig part 2](https://technotes.seastrom.com/2014/11/06/updating-zones-with-tsig-part-2.html)

You're probably eventually going to want to wildcard a zone.  Try this
in your named.conf (it's good practice to put generation dates in your
tsig key name):

```
zone "vpn.example.com" {
        type master ;
        file "master/rs/vpn.example.com-dynamic" ;
        update-policy {
                grant "vpn.example.com-20190205-00" wildcard *.vpn.example.com A AAAA TXT ;

        } ;
} ;
```

Mixing manually updated zones (especially hand edited zone files)
and dynamically updated zones is a recipe for annoyance if not tears.
What to do?  It turns out that ACME will in fact follow a CNAME, even
to a non-child, non-same-origin (I'm tempted to say "out of baliwick"
but the DNS pedants will call me out on subtly incorrect use) zone
without even abusing the [Public Suffix List](https://publicsuffix.org) (cough) which came to me
as a complete surprise to me since I figured such behavior would
constitute an attack surface.

The solution is to designate a zone where you're going to put all of your acme challenge
responses in that zone and CNAME into it for the _acme-challenge records for all your hosts.

Example:

```
$ORIGIN example.org
demo           IN      A	192.0.2.33
_acme-challenge.demo   IN      CNAME   _acme-challenge.demo.example.com.acme.example.com.
```

Note the ORIGIN of example.org and the CNAME pointing to acme.example.com, with the FQDN of
the record being prepended to the dynamic update zone (which need only be updateable for TXT since
that's all you're ever going to put in it).

To support this behavior, set the "acmecnamezone" variable in some appropriate place.

CAVEATS:

1) When you set up your wildcard zone for dynamic updates, reliability is not a criterion.  Velocity
of entire NS-set being on the same page, however, is - you'll be doing an update and then expecting
consistency within a very small number of seconds.  As a result, delegating it to only a single
nameserver will help avoid any transient failures and resultant tearing at one's hair.

2) Speaking of ns-set consistency, if you add the CNAMEs to a zone and one of your nameservers
is lagging behind the others in terms of getting the axfr in (perhaps it's busy, or notify is
broken or something), Murphy's law dictates that the nameserver LetsEncrypt will end up getting
an authoritative answer from is the one that's behind the curve.  Consider doing:

```
dig +nssearch example.org
```

to make sure everything's lined up with the new serial number before you proceed with the playbook.

3) You have to actually do the delegation out of the parent zone with
an NS record.  Merely putting the aforementioned configuration fragment
for the delegated zone in the named.conf is *not sufficient*.  Based
on text conversations I had this morning, I am not the only one who
has forgotten periodically to do this, so it bears repeating.  In
the parent zone, you need:

```
$ORIGIN example.org.
acme	IN	NS	ns.example.org
```

4) If you're using this role at scale, it's probably far easier than
you think to run afoul of LetsEncrypt's [production rate
limits](https://letsencrypt.org/docs/rate-limits/), which you should
read and understand before you try running this role with more than a
couple of dozen hosts in the inventory.  You might think that testing
against LetsEncrypt's [staging
environment](https://letsencrypt.org/docs/staging-environment/) would
be a good way to avoid this, but if you read the docs carefully you'll
see "The staging environment uses the same rate limits as described
for the production environment with the following exceptions"... and
then they go on to enumerate all the ones that you will care about
running afoul of it in real life.  The take-away here is that LE's
"staging environment" is actually a "dev" environment.  Once
you've got things fairly together, if you have doubts you need
to go through an "OT&E" phase with a domain that will not be "hurt"
if you run afoul of the production rate limits.  You have been warned.

5) Using acmecnamezone has turned out to be very pleasant, to the point
that neither G nor R are doing in-zone direct updates.  We added support
for wildcard certs and since setting up a test harness was too much of a
pain, we didn't bother adding support for them under non-acmenamezone
conditions.  If you're thinking "that sounds as if running without
acmezonename is deprecated and support for that configuration may
go away soon", you're probably onto something.

Role Variables
--------------

This role will bomb out if you don't set a bunch of variables before starting.

The usual ClueTrust methodology is to set default values in `inventory_dir/group_vars/all.yml`

You'll probably want these there:

```
host_specific_files: "{{ inventory_dir }}/host_files/{{ inventory_hostname }}"

which_ca: acme-staging-v02.api.letsencrypt.org
# which_ca: acme-v02.api.letsencrypt.org

cert_emailaddress: sslcert@example.com

nsupdate_hmac: hmac-sha256
nsupdate_key_name: vpn.example.com-20190205-00
nsupdate_key_secret: base64-nsupdate-key-secret==
nsupdate_server: ns.example.com

```
Optional (but you probably want):
```
acmecnamezone: "acme.example.org"
```

Note that you can override them per host with files in `inventory_dir/host_vars/inventory_hostname.yml`

In addition to other variables, if you want SANs you should set these
there as they would (probably) not make sense in
`inventory_dir/group_vars/all.yml`:

```
subject_alt_names: 
  - DNS:another.name.example.com
  - DNS:third.name.example.com
  - DNS:*.example.net

```

Note that while you can overwrite which nameserver you're talking to
for which host in your ansible inventory (as well as the key secrets
and such), some kind of multidimensional SAN cert dystopia where
individual hosts need to update domains that are hosted on more than
one nameserver with more than one key was considered to be a bridge
too far.  Sorry, this role doesn't do that.

Optional, but you might find useful (in `all.yml`, `inventory_hostname.yml`, or
passed in via extra\_vars on the command line):
```
force_cert_renew: 'yes'
cert_renew_days: 30
```

If `force_cert_renew` is set to `yes` it will force renewal of the certification, otherwise
the renewal will go based on the `cert_renew_days` variable.

`cert_renew_days` defaults to 60, thus we will renew your certificates if they're at least
30 days old.

To override hostname behavior, you'll want to set:
`cert_hostname` and `cert_hostname_short`, which are by default set to
`inventory_hostname` and `inventory_hostname_short`, but it might be useful to set these
if you're doing SNI on a server which has multiple sites on it.


Encrypting your crypto material
-------------------------------

Because reasons, the openssl module and Ansible Vault don't get along, so if you wish
to keep your crypto material encrypted, you'll have to fall back on a little bit of
included glue that uses the built-in crypto features of OpenSSL.

Variable to do this crypto (Optional, but you might find useful):
```
openssl_passphrase: super-secret
```

If `openssl_passphrase` is present, then created and used keys (account key, .key files) expect to be encrypted
with that passphrase. 

Note that this uses a lookup plugin (`ssl_key_text`) which is built into this role and
decodes an openssl private key using the included passphrase if necessary.

You may want to use this when uploading your key to your server (or you can just put
the passphrase in a file if your server can use that).  To read get the key as
unencrypted PEM format:


```
    - name: copy the key material to the appropriate location
      copy: 
        content: "{{ lookup('ssl_key_text', host_specific_files+'/crypto/server.key', passphrase=(openssl_passphrase if openssl_passphrase is defined else omit)) }}"
        dest: "{{ crypto_dir }}/server.key"
        mode: 0400
        owner: www
        group: www
```

Dependencies
------------

None
(If `ssl_key_text` is used, PyOpenSSL must be present)

Example Playbook
----------------

Including an example of how to use your role (for instance, with variables passed in as parameters) is always nice for users too:

```
- hosts: vpnservers
  gather_facts: no
  tasks:
    - include_role:
        name: letsencrypt-dns01

```

Once you've successfully run this role, you will be rewarded with a series of files
(with traditional-ish names) in
`play_dir/host_files/hostname.vpn.example.org/crypto/`

```
[root@ansible ~/workdir]# ls -l host_files/hostname.vpn.example.org/crypto/
total 33
-rw-r--r-- 1 root root 3566 Feb  6 20:25 server-fullchain.crt
-rw-r--r-- 1 root root 1679 Feb  6 20:25 server-intermediate.crt
-rw-r--r-- 1 root root 1887 Feb  6 20:25 server.crt
-rw-r--r-- 1 root root 1033 Feb  6 20:25 server.csr
-rw------- 1 root root 1704 Feb  6 20:25 server.key
[root@ansible ~/workdir]# 
```

License
-------

MIT

Author Information
------------------

rs@seastrom.com

