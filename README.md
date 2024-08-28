# CSAR Packaging Tool

[TOC]

It is required that the deliverables from applications built on the ADP platform are in the [CSAR](http://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/004/02.03.01_60/gs_nfv-sol004v020301p.pdf) format.
The CSAR package format is a standard from the European Telecommunications Standards Institute [ETSI](https://www.etsi.org/) 

The csar packaging tool takes helm chart(s), VNFD yaml file(s), a manifest file and a name. It returns the CSAR file with the given name.

It does this by:

* executing the `helm template` command on each of the charts
* parsing out the docker image urls
* if any images are in scalar values, for example in a ConfigMap in the service mesh chart
    * executing the `helm inspect values` command on the chart(if --helm3 option is used, then `helm3 show values` command is executed)
    * parsing out the docker image urls
* pulling all the images locally
* executing `docker save` with all the local images
* Bundling all this into the CSAR

## Contributing

We welcome contributions, please see our [contributing](CONTRIBUTING.md) guide for more details.

## Contact 

* Send questions to any of the guardians on the [contributing](CONTRIBUTING.md) page.
* To open a Jira please follow the instructions on [this confluence page](https://confluence-oss.seli.wh.rnd.internal.ericsson.com/display/ESO/How+To+Request+Support+on+E-VNFM)

## Usage

The CSAR Packaging tool has been placed inside a docker image and a script has been created to simplify running the docker image.

The script `run_package_manager.sh` can be downloaded from [Gerrit](https://gerrit.ericsson.se/plugins/gitiles/OSS/com.ericsson.orchestration.mgmt.packaging/am-package-manager/+/refs/heads/master/src/scripts/)

Example command to generate CSAR:

```
run_package_manager.sh <folder containing helm chart> <folder with docker login creds> "<package-manager-arguments>"
```
```
run_package_manager.sh $PWD ~/.docker "--helm my-helm-chart-0.0.1.tgz --name my-csar"
```

The run_package_manager.sh script requires a number of parameters:
* **\<folder containing helm chart(s)\>** the folder containing the helm chart(s) that will be used to generate the CSAR.
* **\<folder with docker login creds\>** the folder that contains the login to the docker registries, typically '~/.docker'.
* **"\<package-manager-arguments\>"** the package manager arguments to be passed to helm. **Please Note**: These arguments must be enclosed in inverted commas.

Mandatory package manager arguments:

* --name or -n:             The name to be given to the generated csar.
* --helm or -hm:            A space separated list of helm charts to package into the csar.
    OR
* --helm-dir or -hd:        The relative path to a directory which contains the helm charts to package into the csar.
* --vnfd or -vn:            The VNF Descriptor .yaml file; must have same prefix as manifest file if the manifest file is provided. This
 param is mandatory if the user intends to onboard the generated CSAR to an ETSI compliant onboarding service.

 **Please Note**: helm and helm-dir parameters can be used at the same time. The list of helm chart files packaged in the CSAR file will be the sum of files of both arguments.

Optional package manager arguments:

* --no-images:              Flag to skip creation of the docker.tar file in the CSAR; default value is false
* --images:                 The path to a pre-packaged file containing the container images exported from the helm chart(s).
* --scripts or -sc:         The path to a folder which contains scripts to be included in the csar file.
* --log or -l:              The level of logging for the package-manager; set to info by default.
* --manifest or -mf:        The path to a manifest file for the csar file.
* --history or -hs:         The change log for the csar file.
* --sha512:                 Option to generate SHA-512 digest for each file in CSAR if manifest file provided; set to true by default.
* --certificate or -cert:   The certificate file for signing of the CSAR manifest file if provided.
* --key:                    The private key for signing of the CSAR manifest file if provided.
* --values-csar or -vc:     The path to the yaml file containing values for generating a manifest file for the CSAR package.
* --definitions or -d:      The path to additional definitions file or directory containing definition files.
* --pkgOption:              To generate signed VNF package, 1 for Option1 and 2 for Option2; Set to 1 by default.
* --helm3:                  To generate CSAR with Helm 3
* --helm-version            Select the helm3 client version to use: 3.4.2, 3.5.1, 3.6.3, 3.7.1 or 3.8.2. Helm 3.4.2 is used default (helm3)
* --scale-mapping or -sm:   The path to a scale-mapping file.
* --product-report:         To generate product report YAML containing Helm chart and Docker image metadata.
* --eric-product-info       To parse eric-product-info.yaml to get images
* --agentk                  Use Agent K to download images
* --disable-helm-template   Disable Helm template parsing to get images
* --timeout                 Docker pull and docker api calls timeout
* --values-cnf-dir or -vcd  The path to a directory with cnf values files. Values files should have the same name as a chart.
* --values-cnf-file or -vcf The path to cnf values yaml file. Values yaml file should have the same name as a chart.
* --licenses or -lcs        The path to the licenses directory for the CSAR file.
* --license or -lc          The path to the license file for the CSAR file.
* --sol-version             SOL version. Version of ETSI GS NFV-SOL 001/004. String format example: 3.3.1
* --eric-product-info-charts The relative path list to Helm charts that eric-product-info.yaml has to be parsed to get images. The list should contain only top-level charts. 
* --extract-crds            Extract CRDs from Helm charts to be packaged separately.

**You must set any required values to render the whole chart to ensure all images are packaged into the csar. Please see the section on passing in values**

**Please Note**: To include a manifest file and a VNFD file, both must share the same name; e.g. *test.yaml* (VNFD file) and *test.mf* (manifest file)

#### The `--images` flag

If you have exported the images of a Helm chart prior to running `am-package-manager` through
some other means, it is possible to copy that file into the CSAR package instead of having
`am-package-manager` generate it.

Simply pass the `--images` flag with the path to that file.

#### The '--pkgOption' flag

There are two package options to create a CSAR file.
The option1 takes the certificate and key files (if provided) to sign a manifest file in accordance with SOL-004 option 1 functionality. Signing is optional and if you do not provide certs, keys and manifests it will not sign.
The option2 functionality takes the key and certificate to sign the generated CSAR as a whole in accordance with SOL-004 option 2 functionality. You must provide a cert and key, else it will fail.

```bash
$ docker run --rm \
  -v $(pwd):$(pwd) \
  -w $(pwd) \
  armdocker.rnd.ericsson.se/proj-am/releases/eric-am-package-manager:1.0.0 \
    generate \
      --helm product-0.1.0.tgz \
      --images product_images.tar \
      --name my_product
```

#### The '--product-report' flag

Generating Product Report tries to parse the given Helm chart and its subcomponents according to [DR-D1121-067](https://confluence.lmera.ericsson.se/display/AA/ADP+IF.HELM.PRODUCT-INFO+Interface+Specification) design rule. If the included components do not conform to this specification the necessary metadata is attempted to be fetched from alternative sources.

For Helm charts the missing information is checked from chart annotations as defined in [DR-D1121-064](https://confluence.lmera.ericsson.se/display/AA/General+Helm+Chart+Structure#GeneralHelmChartStructure-DR-D1121-064), e.g.
```
annotations:
  ericsson.com/product-name: "Diagnostic Data Collector"
  ericsson.com/product-number: "CXD 101 0366"
  ericsson.com/product-revision: 5.1.0
```

For Docker images an alternative source for the product information is Docker image labels based on [DR-D470203-020](https://confluence.lmera.ericsson.se/display/AA/Container+image+design+rules#Containerimagedesignrules-DR-D470203-020), e.g.
```
"Labels": {
    "com.ericsson.product-number": "CXC 174 2971",
    "com.ericsson.product-revision": "R9A",
    "common_base_os": "3.32.0-11",
    "org.opencontainers.image.created": "2021-08-26T14:22:15Z",
    "org.opencontainers.image.revision": "4ee6957",
    "org.opencontainers.image.title": "Service Identity Provider TLS CRD Checker",
    "org.opencontainers.image.vendor": "Ericsson",
    "org.opencontainers.image.version": "2.8.0-35"
}
```

If the information cannot be found from any source a warning message is output but the component is still added to the report with an empty value in the corresponding field.

The output YAML is validated against the generated CSAR package for inconsistencies. The tests contain a cross check between the downloaded images and ones in the Product Report and a check for conflicting product numbers between different components. If the validation does not pass the command returns an error code. Even if the validation fails the output file is still generated. The specific reason for validation failure is output to stdout.

#### The '--agentk' flag

This option enables the use of [Agent K](https://gerrit.ericsson.se/plugins/gitiles/pc/agent-k)
for exporting Docker images.

Agent K is embedded into the am-package-manager image and invoked as a separate binary.

### Prerequisites

* Docker installed and configured.
* Have a active login to each docker registry where images will be pulled from i.e. a  '~/.docker/config.json' file that looks something like this.
```
{
	"auths": {
		"armdocker.rnd.ericsson.se": {
			"auth": "xxxxxxxxxxxxxxxxxxx"
		}
	},
	"HttpHeaders": {
		"User-Agent": "Docker-Client/18.09.3 (linux)"
	}
}
```

### Passing in values

To pass in values during CSAR generation, the user can either input values on the command line or pass in a YAML configuration file which contains the values.

**Please Note**: Users can either input values on the command line *or* pass in a YAML configuration file with the values - both cannot be used at the same time.

All values and files will be passed to each helm chart passed into the tool.

#### To input values using command line:

* Use *--set* as argument
* Input the values as *key=value* format
* These values can be space or comma separated
* If keys are specified more than once, the last value given overall is used by default

Example command to generate CSAR with values on command line:
```
run_package_manager.sh <volume> <credentials-volume> "--helm <helm_chart> --name <csar_name> --set <values>"
```
```
run_package_manager.sh $PWD /home/myuser/.docker "--helm <helm_chart> --name <csar_name> --set ingress.hostname=testname,testkey=testvalue"
```

#### To pass in YAML configuration file:

* Use either *--values* or *-f* as argument
* Only *YAML* files will be accepted - extensions allowed are *.yaml* and *.yml*
* Input the filename(s) including extension, e.g. configFile.yaml, moreValues.yml
* These filenames can be space or comma separated
* The full file path to the YAML configuration file can also be used
* If keys are specified more than once or specified in more than one file, the last value given overall is used by default

Example command to generate CSAR with YAML configuration file containing values passed in:
```
run_package_manager.sh <volume> <credentials-volume> "--helm <helm_chart> --name <csar_name> --values <file_name>"
```
```
run_package_manager.sh $PWD /home/myuser/.docker "--helm <helm_chart> --name <csar_name> --values configFile.yaml extraFile.yml"
```

The configuration file format for passing in values to the helm template requires:

* Must be in correct YAML format
* All values to be listed on *separate* lines
* Values to match *key: value* format
* Comments are allowed but must begin with *#* character and be listed on *separate* lines

Example configuration file:

```
#File to pass in values
testkey: testval
service.account: my-account
#Ingress value
ingress.hostname: testname
```

### To pass in YAML values file for manifest file generation:

* The User can either pass in a values file to generate the manifest file, or pass in a manifest file using --manifest argument. You cannot use both arguments at the same time.
* Use either *--values-csar* or *-vc* as argument
* Only *YAML* files will be accepted - extensions allowed are *.yaml* and *.yml*
* Input the filename including extension, e.g. configFile.yaml, moreValues.yml
* Make sure the required keys are present in the yaml file.

Required Keys:

```
vnf_product_name: Test-Product
vnf_provider_id: Ericsson
vnf_package_version: cxp9025898_4r81e08
vnf_release_date_time: 2017-01-01T10:00+03:00
```

Example command to generate CSAR with YAML configuration file containing values passed in:
```
run_package_manager.sh <volume> <credentials-volume> "--helm <helm_chart> --name <csar_name> --values-csar <file_name>"
```
```
run_package_manager.sh $PWD /home/myuser/.docker "--helm <helm_chart> --name <csar_name> --values-csar manifest-config.yaml"
```

The values file format for passing in values to generate manifest file requires:

* Must be in correct YAML format
* Must include all required keys.
* All values to be listed on *separate* lines
* Values to match *key: value* format
* Comments are allowed but must begin with *#* character and be listed on *separate* lines

### Passing in definition files

To pass in additional files to be used with VNF descriptor, the user can use --definition flag, for example to pass ETSI types definitions files.
You can either pass in a file or a directory containing all the files that need to be added alongside VNF descriptor.

**Please Note**: A nested directory structure is not supported and only the files in the root of the directory passed in will be placed in the Definitions folder of the CSAR package.

### Running the Docker image directly

To retrieve all released docker images by tag look [here](https://arm.epk.ericsson.se/artifactory/docker-v2-global-local/proj-am/releases/eric-am-package-manager/)

```
docker run --rm \
 -v <volume>:/csar \
 -v <credentials-volume>:/root/.docker
 -v /var/run/docker.sock:/var/run/docker.sock \
 -w /csar \
 armdocker.rnd.ericsson.se/proj-am/releases/eric-am-package-manager:{tag} \
 generate <arguments>
```
```
docker run --rm \
 -v /home/myuser/helm_chart:/csar \
 -v /home/myuser/.docker:/root/.docker
 -v /var/run/docker.sock:/var/run/docker.sock \
 -w /csar \
 armdocker.rnd.ericsson.se/proj-am/releases/eric-am-package-manager:1.0.0 \
 generate --helm product.tgz --name my_product
```

* -v <volume>:/csar                         The directory in which the helm chart(s) are stored, and the CSAR will be generated in this directory.
* -v <credentials-volume>:/root/.docker     The directory in which the docker config.json file is stored, this is to allow docker in the container to pull images as a logged in user
* -v docker.sock                            This is needed so that the docker client has access to the docker daemon running on the host to pull images
* -w /csar:                                 The working directory when the container runs

Default helm version is Helm 2. If you want to run it with Helm 3, use '--helm3' option.
```
docker run --rm \
 -v /home/myuser/helm_chart:/csar \
 -v /home/myuser/.docker:/root/.docker
 -v /var/run/docker.sock:/var/run/docker.sock \
 -w /csar \
 armdocker.rnd.ericsson.se/proj-am/releases/eric-am-package-manager:1.0.0 \
 generate --helm product.tgz --name my_product \
 --helm3
```

### Exec into the container and execute the python program

It is also possible to exec into the container to execute the python program.

```
docker run --rm -v $PWD:/csar -v $HOME/.docker:/root/.docker -v /var/run/docker.sock:/var/run/docker.sock -w /csar -it --entrypoint sh armdocker.rnd.ericsson.se/proj-am/releases/eric-am-package-manager:1.0.10-1
```

Once in the container you can execute the python program:

```
eric-am-package-manager generate --helm product.tgz --name my_product
``` 
Default helm version is Helm 2. If you want to run it with Helm 3, use '--helm3' option.
```
eric-am-package-manager generate --helm product.tgz --name my_product --helm3
``` 

### The '--extract-crds' flag

This option collects and extracts all CRDs included in the Helm charts and packages them into CSAR independently along
with the top level Helm chart.

## Develop

All the code resides in the eric_am_package_manager directory.

It is split into two modules and has a dependency on a third module which is in another repo.

* cli
    * The tool is a cli app, this module is the entry point.
    * After parsing and validating the input values it delegates to the generator module and the vnfsdk_pkgtools module
* generator
    * This module puts everything in place for the creation of the csar file
    * Pulls the docker images
    * Creates the docker tar file
    * Creates the directory structure expected by the vnfsdk_pkgtools module

* vnfsdk_pkgtools
    * This resides in [this repo](https://gerrit.ericsson.se/#/admin/projects/OSS/com.ericsson.orchestration.mgmt.packaging/vnfsdk-pkgtools)
    * It is a fork of an open source repo
    * We forked it because it didn't support storing Helm and they didn't accept our contribution: https://github.com/onap/vnfsdk-pkgtools/pull/1

### Keeping the Fork up to Date

```bash
# configure upstream remote
git remote add upstream https://gerrit.onap.org/r/vnfsdk/pkgtools

# Get all the changes from the onap vnfsdk-pkgtools repo
git pull upstream master

# get the latest changes from our forked repo
git fetch

# apply our changes on top of the changes from the onap repo
git rebase origin master

# push the upstream changes to origin master
git push origin master
```

## Test

### Unit Tests

All the unit tests reside in the tests directory.

Its structure mirrors that of the eric_am_package_manager directory.

### Acceptance Tests

There are a number of acceptance tests in the repo written using the robot framework.

They reside in the tests/robot folder.

### Manual Testing

The easiest way to test the tool is to build the docker image and run it.
The instructions for running the docker image directly are described above.

Happy manual testing

## Build

Building and releasing a python module is not as straight forward as we are used to in the java world. That is why we have put the module inside a docker image.

The maven-exec-plugin is used several times to execute pip and python commands to create a whl file which is copied into the Dockerfile. A whl file is an installer file for a python module.

The vnfsdk-pkgtools dependency is in the base image.

mvn clean install does the following:

* Installs the am-package-manager
* Executes the unit tests
* Builds the whl file

### Prerequisite for building locally

To build the project on your laptop the vnfsdk module is required.

Information below is out of date. Better to use docker image.
```bash
# Download the tar file
wget https://arm101-eiffel052.lmera.ericsson.se:8443/nexus/service/local/repositories/eso-repository/content/com/ericsson/orchestration/mgmt/packaging/vnfsdk-pkgtools/0.0.5/vnfsdk-pkgtools-0.0.5.tar.gz

# Extract the contents
tar -xvf vnfsdk-pkgtools-0.0.5.tar.gz

# Install the module
pip install vnfsdk-pkgtools-0.0.5/vnfsdk-0.0.5-py2-none-any.whl

```

## Release

Jenkins jobs currently sit [here](https://fem4s11-eiffel052.eiffel.gic.ericsson.se:8443/jenkins/view/am-package-manager/)


### Update Version of vnfsdk_pkgtools

Jenkins jobs for vnfsdk_pkgtools are [here](https://fem4s11-eiffel052.eiffel.gic.ericsson.se:8443/jenkins/view/vnfsdk-pkgtools/)
Once the new version is released you need to update the version in the **Dockerfile** in this repo

## Limitations

### External Credential Store

The package manager tool does not yet work with systems that store user credentials in an external credential store .i.e a system that has a  '~/.docker/config.json' that looks like this
 ```
{
	"auths": {},
	"HttpHeaders": {
		"User-Agent": "Docker-Client/18.09.7 (linux)"
	},
	"credsStore": "secretservice"
}
```  
There current workaround is to delete the '~/.docker/config.json' file and login to the docker registry e.g.
```
docker login armdocker.rnd.ericsson.se
```
This will create a new '~/.docker/config.json' in a format that works with the current package manager.

### Docker registries with Port numbers

The [docker python library](https://github.com/docker/docker-py) we use does not support repositories with port numbers.

For example, my.registry.ericsson.se:5000/my-project/image:1.2.3 will not be pulled as the library takes the port number as the tag of the image.

You can generate the docker.tar file separately from the packaging tool, and add it using the --images argument.

There is another inner source tool which can generate a docker.tar of images from a helm chart: https://gerrit.ericsson.se/plugins/gitiles/pc/agent-k/+/refs/heads/master

### Upscaling mapping

Use `--scale-mapping` or `"-sm"` argument to provide a scale-mapping file.
Now you can create csar with this command:

```
$ docker run --rm \
  -v $(pwd):$(pwd) \
  -w $(pwd) \
  armdocker.rnd.ericsson.se/proj-am/releases/eric-am-package-manager:1.0.0 \
    generate \
      --helm product-0.1.0.tgz \
      --images product_images.tar \
      --scale-mapping scaling_mapping.yaml

```
**Please Note**:The mapping file shall be stored in the Definitions\OtherTemplates when CSAR is built. **
