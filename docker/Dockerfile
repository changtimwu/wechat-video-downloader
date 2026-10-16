# WeChat for Linux + transparent mitmproxy capture, all inside one container.
# The host only runs Docker: no system proxy, no CA in the host keychain.
#
#   docker compose up -d --build     then open http://127.0.0.1:3000

ARG WEBTOP_TAG=ubuntu-xfce-36e96c40-ls6
FROM lscr.io/linuxserver/webtop:${WEBTOP_TAG}

# Official build; TARGETARCH picks arm64 or x86_64.
ARG TARGETARCH
ARG WECHAT_DEB_BASE=https://dldir1v6.qq.com/weixin/Universal/Linux

ENV LANG=zh_CN.UTF-8 \
    LC_ALL=zh_CN.UTF-8 \
    LIBGL_ALWAYS_SOFTWARE=1 \
    QT_X11_NO_MITSHM=1 \
    NO_AT_BRIDGE=1

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        ca-certificates curl locales iptables libnss3-tools \
        python3 python3-venv \
        fonts-noto-cjk fonts-noto-color-emoji \
        libnss3 libgbm1 libasound2t64 libxss1 libatomic1 libxdamage1 \
        libxkbcommon-x11-0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
        libxcb-render-util0 libxcb-xkb1 libxcb-cursor0 libgtk-3-0t64 \
        libatk1.0-0t64 libatk-bridge2.0-0t64 libatspi2.0-0t64 libcups2t64 \
        libxcomposite1 libxrandr2 libxfixes3 libxtst6 libxshmfence1 libdrm2; \
    case "$TARGETARCH" in arm64) wx=arm64 ;; amd64) wx=x86_64 ;; *) echo "unsupported arch $TARGETARCH"; exit 1 ;; esac; \
    curl -fL --retry 3 -o /tmp/wechat.deb "$WECHAT_DEB_BASE/WeChatLinux_$wx.deb"; \
    apt-get install -y --no-install-recommends /tmp/wechat.deb; \
    sed -i 's/# *zh_CN.UTF-8 UTF-8/zh_CN.UTF-8 UTF-8/' /etc/locale.gen; \
    locale-gen; \
    useradd --system --no-create-home --shell /usr/sbin/nologin mitm; \
    rm -f /tmp/wechat.deb; \
    apt-get clean; rm -rf /var/lib/apt/lists/*

# wxvd (capture addon + CLI) in its own venv.
COPY pyproject.toml README.md /src/
COPY wxvd /src/wxvd
RUN set -eux; \
    python3 -m venv /opt/wxvd; \
    /opt/wxvd/bin/pip install --no-cache-dir "/src[capture]"; \
    ln -s "$(/opt/wxvd/bin/python -c 'import wxvd.capture as m; print(m.__file__)')" /opt/wxvd/capture.py; \
    ln -s /opt/wxvd/bin/wxvd /usr/local/bin/wxvd

COPY docker/rootfs/ /
RUN chmod +x /custom-cont-init.d/* /custom-services.d/*

EXPOSE 3000 3001
