## CLARIAH Structured Data Hub API
**Author:**	Rinke Hoekstra  
**Copyright:**	Rinke Hoekstra, VU University Amsterdam  
**License:**	MIT License (see [license.txt](license.txt))  

### Installation

First, open a terminal or console and clone this git repository to a directory of your choice:

`git clone https://github.com/CLARIAH/wp4-csdh-api.git`  
(you can also download the source from Github)

Change directory to directory and then (to keep things nice and tidy) use [virtualenv](https://virtualenv.pypa.io/en/latest/installation.html) to create a virtual environment, and activate it:

`virtualenv .`

and

`source bin/activate` (on unix/linux-style systems)

Then install the required Python packages using [pip](https://pip.readthedocs.org):

`pip install -r requirements.txt`

Copy the `config_template.py` file to `config.py` and make necessary changes (see documentation in the file).

Change directory to `src` and then:

`python run.py`

the API will be running on <http://localhost:5000> (click this link, or copy it to your browser).

Go to <http://localhost:5000/specs> to view the API specs in JSON schema format (Swagger)

Make sure to always activate the `virtualenv` before running the API again.
