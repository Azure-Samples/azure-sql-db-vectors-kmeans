FROM continuumio/miniconda3:24.1.2-0

# apt-get and system utilities
RUN apt-get update && apt-get install -y \
	curl apt-transport-https debconf-utils gnupg2 

# adding custom MS repository
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
RUN curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list

# install AZ CLI
RUN curl -sL https://aka.ms/InstallAzureCLIDeb | bash

# install SQL Server drivers and tools
RUN apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql18 mssql-tools18
RUN echo 'export PATH="$PATH:/opt/mssql-tools18/bin"' >> ~/.bashrc
RUN /bin/bash -c "source ~/.bashrc"
RUN apt-get -y install locales \
    && rm -rf /var/lib/apt/lists/*
RUN locale-gen en_US.UTF-8
RUN localedef -i en_US -f UTF-8 en_US.UTF-8

# install packages
RUN conda install -c conda-forge \
    scikit-learn \    
    pyodbc \
    python-multipart python-dotenv \    
    uvicorn[standard] \
    fastapi apscheduler \
    azure-identity \
    -y

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:api", "--host", "0.0.0.0", "--port", "8000"]
