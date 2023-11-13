#!/usr/bin/bash

create_shims() {
    _APPID="$1"
    _COMMAND="$2"
    shim="$HOME/.local/bin/$_COMMAND"

    cat > $shim << EOF
#!/usr/bin/env sh
exec flatpak run $_APPID "\$@"
EOF
    chmod +x $shim
}

flatpak list --app --columns=application | while read _APPID; do
    _CMD="$(flatpak info -m $_APPID | awk -F= '/^command=/ {print $2}')"
    _CMD="$(basename $_CMD)"

    create_shims "$_APPID" "$_CMD"
done