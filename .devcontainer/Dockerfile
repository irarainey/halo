FROM python:3.13-slim

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && apt-get update && apt-get install -y \
        sudo \
        curl \
        wget \
        git \
        vim \
        nano \
        less \
        jq \
        htop \
        tree \
        unzip \
        zip \
        tar \
        gzip \
        ca-certificates \
        gnupg \
        openssh-client \
        procps \
        net-tools \
        iputils-ping \
        dnsutils \
        lsof \
        strace \
        build-essential \
        zsh \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME \
    && rm -rf /var/lib/apt/lists/*

USER $USERNAME
RUN sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended
USER root

RUN chsh -s /usr/bin/zsh $USERNAME

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

ENV UV_LINK_MODE=copy
