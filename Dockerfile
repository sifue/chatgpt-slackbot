FROM python:3.9
USER root

RUN apt-get update
RUN apt-get -y install locales && \
localedef -f UTF-8 -i ja_JP ja_JP.UTF-8
ENV LANG ja_JP.UTF-8
ENV LANGUAGE ja_JP:ja
ENV LC_ALL ja_JP.UTF-8
ENV TZ JST-9
ENV TERM xterm

RUN apt-get install -y vim less
RUN pip install --upgrade pip
RUN pip install --upgrade setuptools

RUN python -m pip install python-dotenv --upgrade
RUN python -m pip install openai==1.12.0
RUN python -m pip install tiktoken --upgrade
RUN python -m pip install slack_bolt --upgrade
RUN python -m pip install duckduckgo_search --upgrade

CMD cd /root/opt/ && python app.py
