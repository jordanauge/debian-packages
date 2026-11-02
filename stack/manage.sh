#!/bin/sh
set -eu
umask 022
base=/repository
case "${1:-}" in
    init)
        install -d -m 700 "$GNUPGHOME"
        install -d "$base/public" "$base/private" "$base/incoming" "$base/auth"
        if [ ! -e "$base/auth/htpasswd" ]; then
            install -m 644 /dev/null "$base/auth/htpasswd"
        fi
        if ! gpg --batch --list-secret-keys --with-colons | grep -q '^sec:'; then
            gpg --batch --pinentry-mode loopback --passphrase '' \
                --quick-generate-key 'Synaxe Debian Archive <packages@synaxe.org>' rsa3072 sign 2y
        fi
        fingerprint=$(gpg --batch --list-secret-keys --with-colons | awk -F: '$1=="fpr" {print $10; exit}')
        gpg --batch --armor --export "$fingerprint" > "$base/public/synaxe-archive-keyring.asc"
        for tree in public private; do
            components="main thirdparty"
            [ "$tree" != private ] || components=private
            install -d "$base/$tree/conf"
            printf 'Origin: Synaxe\nLabel: Synaxe %s\nCodename: forky\nArchitectures: amd64 arm64 source\nComponents: %s\nDescription: Synaxe package archive\nSignWith: %s\n' \
                "$tree" "$components" "$fingerprint" > "$base/$tree/conf/distributions"
            reprepro -b "$base/$tree" export
        done
        python3 /usr/local/bin/catalogue.py "$base"
        printf 'Archive key fingerprint: %s\n' "$fingerprint"
        ;;
    publish)
        tree=${2:?public or private required}
        component=${3:?component required}
        shift 3
        case "$tree:$component" in public:main|public:thirdparty|private:private) ;;
            *) echo "Invalid archive/component" >&2; exit 2 ;;
        esac
        [ "$#" -gt 0 ] || { echo "No package supplied" >&2; exit 2; }
        for package do
            reprepro -b "$base/$tree" -C "$component" includedeb forky "$package"
        done
        python3 /usr/local/bin/catalogue.py "$base"
        ;;
    user)
        username=${2:?username required}
        case "$username" in ''|*[!A-Za-z0-9._@+-]*) echo "Invalid username" >&2; exit 2 ;; esac
        echo "Enter the new password on standard input." >&2
        htpasswd -iB "$base/auth/htpasswd" "$username"
        ;;
    issue)
        python3 /usr/local/bin/credentials.py "${2:?username required}"
        ;;
    list)
        reprepro -b "$base/${2:-public}" list forky
        ;;
    *) echo "Usage: manage.sh init | publish TREE COMPONENT DEB... | issue USER | user USER | list [TREE]" >&2; exit 2 ;;
esac
