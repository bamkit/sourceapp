from django.db import models
from django.utils import timezone

class File(models.Model):
    name = models.CharField(max_length=255, unique=True)
    uploaded_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name

class Polygon(models.Model):
    name = models.CharField(max_length=100)
    coordinates = models.TextField()  # Store as JSON string

    def __str__(self):
        return self.name
    
class PreplotLine(models.Model):
    loaded = models.BooleanField(default=False)
    preplot = models.IntegerField()
    shotpoint1 = models.IntegerField(default=0)
    eastings1 = models.FloatField()
    northings1 = models.FloatField()
    latitude1 = models.FloatField()
    longitude1 = models.FloatField()
    shotpoint2 = models.IntegerField(default=0)
    eastings2 = models.FloatField()
    northings2 = models.FloatField()
    latitude2 = models.FloatField()
    longitude2 = models.FloatField()

    def __str__(self):
        return f"Line {self.preplot}: {self.shotpoint1} - {self.shotpoint2}"
    
class PreplotShotPoints(models.Model):
    preplot = models.ForeignKey(PreplotLine, on_delete=models.CASCADE, related_name='ppsp')
    shotpoint = models.IntegerField()
    easting = models.FloatField()
    northing = models.FloatField()
    latitude = models.FloatField()
    longitude = models.FloatField()

    def __str__(self):
        return f"SP {self.shotpoint}"


class Sequence(models.Model):
    preplot = models.ForeignKey(PreplotLine, null=True, on_delete=models.CASCADE, related_name='sequence')
    type = models.IntegerField()
    pass_number = models.IntegerField()
    sequence_number = models.IntegerField()
    linename = models.CharField(null=True, max_length=255)
    
    def __str__(self):
        return f"{self.linename}"

class AcquisitionShotPoint(models.Model):
    sequence = models.ForeignKey(Sequence, null=True, on_delete=models.CASCADE, related_name='details')
    sp = models.IntegerField()
    lat = models.FloatField()
    long = models.FloatField()
    east = models.FloatField()
    north = models.FloatField()
    depth = models.FloatField()
    datetime = models.DateTimeField()
    zlat1 = models.FloatField()
    zlon1 = models.FloatField()
    zlat2 = models.FloatField()
    zlon2 = models.FloatField()
    zlat3 = models.FloatField()
    zlon3 = models.FloatField()
    mean_lat = models.FloatField()
    mean_lon = models.FloatField()

    def __str__(self):
        return f"{self.sequence.linename} - SP {self.sp}"
