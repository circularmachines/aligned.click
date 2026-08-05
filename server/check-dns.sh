#!/usr/bin/env bash
# Check the six records that have to survive a nameserver move.
#
# Two of them are identities. `_atproto.johan.aligned.click` is what makes the
# handle resolve to a DID, so if it does not come back up the Bluesky account
# breaks, the OAuth login breaks, and everything already published loses its
# author. This is the script to run before switching nameservers (against the
# new servers, with `-s`) and again after.
#
#     ./server/check-dns.sh                        # ask the public internet
#     ./server/check-dns.sh -s bob.ns.cloudflare.com   # ask the new zone directly
set -uo pipefail

SERVER=""
[ "${1:-}" = "-s" ] && SERVER="@${2:-}"

ask() { dig +short "$2" "$1" $SERVER 2>/dev/null | tr '\n' ' ' | sed 's/ *$//'; }

check() {
  local name="$1" type="$2" want="$3" got
  got="$(ask "$name" "$type")"
  if [ -z "$got" ]; then
    printf '  \033[31mMISSING\033[0m  %-30s %-5s (expected %s)\n' "$name" "$type" "$want"
    return 1
  elif [[ "$got" == *"$want"* ]]; then
    printf '  \033[32mok\033[0m       %-30s %-5s %s\n' "$name" "$type" "$got"
  else
    printf '  \033[31mWRONG\033[0m    %-30s %-5s got %s, wanted %s\n' "$name" "$type" "$got" "$want"
    return 1
  fi
}

fail=0
echo "identities — these breaking is the whole risk:"
check _atproto.aligned.click       TXT   "did:plc:kdnkzvtg6nugup477ev22xfa" || fail=1
check _atproto.johan.aligned.click TXT   "did:plc:evocjxmi5cps2thb4ya5jcji" || fail=1
echo
echo "the rest:"
check _lexicon.chat.aligned.click  TXT   "did:plc:kdnkzvtg6nugup477ev22xfa" || fail=1
check aligned.click                A     ""                                 || fail=1
check read.aligned.click           CNAME "circularmachines.github.io"       || fail=1

# Informational, never a failure. The SPF line belongs to Namecheap's email
# forwarding, which only works on Namecheap's nameservers — so moving the zone
# is exactly when it *should* disappear. Its absence means mail to @aligned.click
# stops arriving, quietly and without a bounce, which is worth being told twice
# rather than being failed for.
spf="$(ask aligned.click TXT)"
mx="$(ask aligned.click MX)"
if [ -z "$mx" ]; then
  printf '  \033[33mnote\033[0m     %-30s %s\n' "aligned.click" "no MX — mail to @aligned.click goes nowhere"
  printf '           %-30s %s\n' "" "(Cloudflare Email Routing replaces it, free)"
else
  printf '  \033[32mok\033[0m       %-30s %-5s %s\n' "aligned.click" "MX" "$mx"
  [ -z "$spf" ] && printf '  \033[33mnote\033[0m     %-30s %s\n' "aligned.click" "MX but no SPF — mail may be marked as spam"
fi

echo
echo "handles resolving — note this asks the public internet, not the server"
echo "above, so before a switch it only proves nothing has broken yet:"
for handle in aligned.click johan.aligned.click; do
  got="$(curl -s "https://bsky.social/xrpc/com.atproto.identity.resolveHandle?handle=$handle" \
        | sed -n 's/.*"did":"\([^"]*\)".*/\1/p')"
  if [ -n "$got" ]; then
    printf '  \033[32mok\033[0m       %-30s %s\n' "$handle" "$got"
  else
    printf '  \033[31mBROKEN\033[0m   %-30s does not resolve\n' "$handle"; fail=1
  fi
done

echo
if [ "$fail" = 0 ]; then
  echo "all good."
else
  echo "something is missing — do not switch nameservers until it is not."
  exit 1
fi
