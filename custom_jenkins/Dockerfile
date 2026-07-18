FROM jenkins/jenkins:lts

USER root

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
      apt-transport-https \
      ca-certificates \
      curl \
      gnupg \
      software-properties-common && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add - && \
    echo "deb [arch=amd64] https://download.docker.com/linux/debian bullseye stable" \
      > /etc/apt/sources.list.d/docker.list && \
    apt-get update -y && \
    apt-get install -y --no-install-recommends docker-ce docker-ce-cli containerd.io && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN groupadd -f docker && \
    usermod -aG docker jenkins

RUN mkdir -p /var/lib/docker
VOLUME /var/lib/docker

USER jenkins
