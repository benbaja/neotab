The stack in a nutshell :
-

Neotab runs mostly on python. It uses Flask to create a webserver, Flask uses different URL routes to display what's showing on the screen, from HTML documents called "templates" that can be populated in a pythonic way (text, MSDS, etc).

HTML documents are stylized with Bootstrap, a super easy to use framework that saves time from working with CSS and javascript. Please not that you should use version 4.6.2 since older tablets can't handle the most recent javascript or CSS5 updates that Bootstrap uses.

When Neotab is ran for the first time (or when Refresh DB is pressed), it queries the containers database (for entities types consumables and reagents) from API calls. This takes a while.

The database is stored "locally" on the machine running (but actually server side using a "virtual cookie" hack but it's invisible) so refreshing the DB only acts on the local machine.

When modifications are added to a container through Neotab, it sends an API call to Benchling.
When a container is requested to order more, it sends an API call to Notion to add it to a database


How to change stuff locally :
-

- pull the latest version from GitLab (git pull)
- create a virtual environment (python -m venv neotab_venv) [FIRST TIME ONLY]
- edit the activation file to add the USE_TEST_INSTANCE VARIABLE [FIRST TIME ONLY]
    - edit the file (nano neotab_venv/bin/activate) and add these lines after the "deactivate" function
    - USE_TEST_INSTANCE="False"
    - export USE_TEST_INSTANCE
- activate the virtual environment (source neotab_venv/bin/activate)
- using pip, install all the requirements (pip -r requirements.txt) [FIRST TIME ONLY]
- run the flask app (flask run --debug)
- open http://127.0.0.1:5000 to see neotab running locally. When the code changes, it will refresh automatically
- once you're done applying your changes, push to the GitLab repo
    - (git add -A)
    - (git commit -m "a description of your changes")
    - (git push)
- see "how to deploy online" for the next steps

Difference between test and production version
-

Test version use the test instance of benchling (neoplantstest.benchling.com), that should mirror the data model of the production version (neoplants.benchling.com)

USE TEST VERSION IF TESTING FEATURES USING BENCHLING API CALLS (mark as opened, mark as empty, move etc)

A pop-up on top of the screen should warn you if you are running the test version


How to deploy online
- Install Docker on your computer [FIRST TIME ONLY]
- Run docker
- Open a terminal in the neotab directory
- Input the following commands to build and push the container to the 
    - (docker login registry.gitlab.com)
    - (docker buildx build --platform linux/amd64 -t registry.gitlab.com/neoplants/neotab .)
    - (docker push registry.gitlab.com/neoplants/neotab)
- SSH to the NAS (ssh neoadmin@10.10.0.55 -p 26)
- login as administrator on the NAS (sudo -i)
- pull the latest Neotab image (docker pull registry.gitlab.com/neoplants/neotab:latest)
- log on Synology (http://10.10.0.55:5020/)
- open Docker and go to the container tab, stop and delete the "neotab" container running
- go to the Image tab, and double click on the neotab one
- name the container "Neotab" and go to advanced settings : make sure that "USE_TEST_INSTANCE" is set to False
- in "Port Settings", set the local port to 49155 and the container port to 5000
- start the container and go to http://10.10.0.55:49155



Cool ressources :
-

- Flask docs https://flask.palletsprojects.com/en/3.0.x/
- Benchling API reference https://benchling.com/api/reference#/Containers/transferIntoContainer
- Benchling API guide https://docs.benchling.com/docs
- Benchling SDK reference https://benchling.com/sdk-docs/1.7.0/index.html