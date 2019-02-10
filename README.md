```
pip3 install Jinja2
pip3 install Django
python3 -m django --version
django-admin startproject website
cd website
python manage.py runserver
```

# TODO
* Comparer les prix Spot et Reserved

* Faire une liste de toutes les commandes liées aux instances Spot et présenter les fonctionnalités associées : 
  https://docs.aws.amazon.com/cli/latest/reference/ec2/index.html#cli-aws-ec2

* Trick pour avoir du On-Demand et du Spot en même temps
  https://serverfault.com/questions/593744/spot-instances-frequently-terminated-in-aws-auto-scaling-group-failing-system-h
  BEAUCOUP MIEUX: Utiliser une MixedInstancesPolicy

* Regarder SpotInst

