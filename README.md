### Virtual Sensor
A virtual sensor for smartcity middleware that has subscriber and provider calls.

#### DEMO
http://sensordemo-rbccps.193b.starter-ca-central-1.openshiftapps.com/

#### Local deployment using docker and Source-To-Image (S2I) tool

Source-to-Image (S2I) is a toolkit and workflow for building reproducible Docker images from source code. S2I produces
ready-to-run images by injecting source code into a Docker container and letting the container prepare that source code for execution. By creating self-assembling **builder images**, you can version and control your build environments exactly like you use Docker images to version your runtime environments.

Download the [latest release](https://github.com/openshift/source-to-image/releases/latest) of s2i and run to get app hosted:

    $ s2i build https://github.com/harishanand95/virtualsensor centos/python-35-centos7 virtualsensor

    $ docker run -p 8080:8080 virtualsensor
