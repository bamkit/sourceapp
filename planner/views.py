import csv
import re
import os
# import tempfile
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.shortcuts import render, get_object_or_404
from django.views import View
from django.contrib import messages
from .models import File, PreplotShotPoints, Polygon, PreplotLine
from .models import Sequence, AcquisitionShotPoint
from .forms import CSVUploadForm
import json
from django.http import JsonResponse
from pyproj import CRS, Transformer
from django.shortcuts import redirect
# from django.db import transaction
from .functions import *
import pandas as pd
from background_task import background
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone
from math import sqrt, atan2, degrees


class HomeView(View):

    def get(self, request):
        # def get(self, request):
        files = File.objects.all()
        points = PreplotShotPoints.objects.all()
        polygon = Polygon.objects.first()
        sequences = Sequence.objects.all()

        # Fetch first and last shotpoints for each Sequence
        sequence_points = []
        for sequence in sequences:
            first_point = AcquisitionShotPoint.objects.filter(
                sequence=sequence).order_by('datetime').first()
            last_point = AcquisitionShotPoint.objects.filter(
                sequence=sequence).order_by('datetime').last()

            if first_point and last_point:
                sequence_points.extend([{
                    'lat': first_point.mean_lat,
                    'lon': first_point.mean_lon,
                    'sp': first_point.sp,
                    'depth': first_point.depth,
                    'sequence_name': sequence.linename,
                    'point_type': 'First'
                }, {
                    'lat': last_point.mean_lat,
                    'lon': last_point.mean_lon,
                    'sp': last_point.sp,
                    'depth': last_point.depth,
                    'sequence_name': sequence.linename,
                    'point_type': 'Last'
                }])

        # Add P190 lines data
        lines = PreplotLine.objects.all()
        lines_data = [{
            'id': line.id,
            'preplot': line.preplot,
            'latitude1': line.latitude1,
            'longitude1': line.longitude1,
            'shotpoint1': line.shotpoint1,
            'latitude2': line.latitude2,
            'longitude2': line.longitude2,
            'shotpoint2': line.shotpoint2
        } for line in lines]

        context = {
            'files': files,
            'points': points,
            'polygon': polygon,
            'preplot_lines': json.dumps(lines_data),
            'sequence_points': json.dumps(sequence_points)
        }
        return render(request, 'planner/home.html', context)


class DisplayPointsView(View):

    def get(self, request):
        files = File.objects.all()
        points = PreplotShotPoints.objects.all()
        polygon = Polygon.objects.first()
        sequences = Sequence.objects.all()

        # Fetch first and last shotpoints for each Sequence
        sequence_points = []
        for sequence in sequences:
            first_point = AcquisitionShotPoint.objects.filter(
                sequence=sequence).order_by('datetime').first()
            last_point = AcquisitionShotPoint.objects.filter(
                sequence=sequence).order_by('datetime').last()

            if first_point and last_point:
                sequence_points.extend([{
                    'lat': first_point.mean_lat,
                    'lon': first_point.mean_lon,
                    'sp': first_point.sp,
                    'depth': first_point.depth,
                    'linename': sequence.linename,
                    'point_type': 'First'
                }, {
                    'lat': last_point.mean_lat,
                    'lon': last_point.mean_lon,
                    'sp': last_point.sp,
                    'depth': last_point.depth,
                    'linename': sequence.linename,
                    'point_type': 'Last'
                }])

        # Add P190 lines data
        lines = PreplotLine.objects.all()
        lines_data = [{
            'preplot': line.preplot,
            'latitude1': line.latitude1,
            'longitude1': line.longitude1,
            'latitude2': line.latitude2,
            'longitude2': line.longitude2
        } for line in lines]

        context = {
            'files': files,
            'points': points,
            'polygon': polygon,
            'preplot_lines': json.dumps(lines_data),
            'sequence_points': json.dumps(sequence_points)
        }
        return render(request, 'planner/display.html', context)


class UploadPolygonView(View):

    def post(self, request):
        polygon_data = json.loads(request.POST['polygon'])
        Polygon.objects.all().delete()  # Remove existing polygon
        Polygon.objects.create(name="Uploaded Polygon",
                               coordinates=json.dumps(polygon_data))
        return redirect('display_points')


class LoadPreplotView(View):

    def get(self, request):
        preplot = PreplotLine.objects.first()

        if preplot is None:
            messages.error(
                request,
                'No preplot data available. Please upload a preplot file first.'
            )
            return render(request, 'planner/load_preplot.html')
        elif preplot.loaded:
            messages.success(request, 'Preplot file already loaded.')
            return redirect('home')

        return render(request, 'planner/load_preplot.html'
                      )  # Added this to display the form if no errors

    def post(self, request):
        # Check if file exists in the request
        if 'preplot_file' not in request.FILES:
            messages.error(request, 'No file was uploaded.')
            return redirect('load_preplot')

        # Check if "preplot_type" is provided in POST data
        preplot_type = request.POST.get('preplot_type')
        if not preplot_type:
            messages.error(request, 'Please select a preplot type.')
            return redirect('load_preplot')

        # Only proceed if "3D" is selected
        if preplot_type == "3D":
            # Get the uploaded file
            preplot_file = request.FILES['preplot_file']

            # Validate the file extension
            if not preplot_file.name.endswith('.p190'):
                messages.error(
                    request, 'Invalid file type. Please upload a .p190 file.')
                return redirect('load_preplot')

            # Process the preplot file for 3D type
            preplot_df = get_preplot_coordinates(preplot_file)

            preplot_lines = []

            # Check for existing preplot lines to avoid duplicate creation
            existing_lines = set(
                PreplotLine.objects.values_list('preplot', flat=True))

            for index, row in preplot_df.iterrows():
                preplot_id = int(row['linename'])

                # Skip if preplot line already exists
                if preplot_id in existing_lines:
                    continue

                preplot_line = PreplotLine(loaded=True,
                                           preplot=preplot_id,
                                           shotpoint1=int(row['sp1']),
                                           eastings1=float(row['east1']),
                                           northings1=float(row['north1']),
                                           latitude1=float(row['lat1_deg']),
                                           longitude1=float(row['lon1_deg']),
                                           shotpoint2=int(row['sp2']),
                                           eastings2=float(row['east2']),
                                           northings2=float(row['north2']),
                                           latitude2=float(row['lat2_deg']),
                                           longitude2=float(row['lon2_deg']))
                preplot_lines.append(preplot_line)

            # Bulk create new PreplotLines
            PreplotLine.objects.bulk_create(preplot_lines)

            messages.success(
                request,
                f'Successfully loaded {preplot_file.name}. Processed {len(preplot_lines)} new lines.'
            )

            # Process shotpoints for each preplot line
            preplot_lines_dict = get_preplot_shots(preplot_df)

            # Fetch all relevant PreplotLines once, to avoid querying inside the loop
            preplot_line_map = {
                pl.preplot: pl
                for pl in PreplotLine.objects.filter(
                    preplot__in=preplot_lines_dict.keys())
            }

            preplot_shotpoints = []

            for line_name, preplotshots_df in preplot_lines_dict.items():
                preplot_line = preplot_line_map.get(int(line_name))

                if preplot_line:
                    for index, row in preplotshots_df.iterrows():
                        shotpoint = PreplotShotPoints(
                            preplot=preplot_line,
                            shotpoint=int(row['sp']),
                            easting=float(row['east']),
                            northing=float(row['north']),
                            latitude=float(row['lat']),
                            longitude=float(row['lon']))
                        preplot_shotpoints.append(shotpoint)

            # Bulk create PreplotShotPoints
            PreplotShotPoints.objects.bulk_create(preplot_shotpoints)

            messages.success(
                request,
                f'Successfully processed {len(preplot_lines)} lines and {len(preplot_shotpoints)} shotpoints.'
            )

        else:
            # Handle the "4D" case or other types as needed
            messages.info(
                request,
                'Preplot type 4D selected. Please ensure you have the appropriate processing logic for this type.'
            )

        if preplot_type == "4D":
            # Get the uploaded file
            preplot_file = request.FILES['preplot_file']

            # Validate the file extension
            if not preplot_file.name.endswith('.p190'):
                messages.error(
                    request, 'Invalid file type. Please upload a .p190 file.')
                return redirect('load_preplot')

            # Process the preplot file for 3D type
            preplot_df = get_4d_preplot(preplot_file)

            preplot_lines_df = get_4d_preplot_endpoints(preplot_df)

            preplot_lines = []
            
            # Check for existing preplot lines to avoid duplicate creation
            existing_lines = set(PreplotLine.objects.values_list('preplot', flat=True))

            for index, row in preplot_lines_df.iterrows():
                preplot_id = int(row['linename'])

                # Skip if preplot line already exists
                if preplot_id in existing_lines:
                    continue

                preplot_line = PreplotLine(loaded=True,
                                           preplot=preplot_id,
                                           shotpoint1=int(row['sp1']),
                                           eastings1=float(row['east1']),
                                           northings1=float(row['north1']),
                                           latitude1=float(row['lat1_deg']),
                                           longitude1=float(row['lon1_deg']),
                                           shotpoint2=int(row['sp2']),
                                           eastings2=float(row['east2']),
                                           northings2=float(row['north2']),
                                           latitude2=float(row['lat2_deg']),
                                           longitude2=float(row['lon2_deg']))
                preplot_lines.append(preplot_line)

            # Bulk create new PreplotLines
            PreplotLine.objects.bulk_create(preplot_lines)

            messages.success(
                request,
                f'Successfully loaded {preplot_file.name}. Processed {len(preplot_lines)} new lines.'
            )

        return redirect('home')  # Redirect after successful upload


@background(schedule=60)
def process_sequence_file(file_path):
    try:
        # Read the file using Django's storage system
        with default_storage.open(file_path) as file:
            df = srecords_to_df(file)

        filename = os.path.basename(file_path)

        # Convert jday and time to a single datetime column
        df['datetime'] = pd.to_datetime(df['jday'].astype(str) + ' ' +
                                        df['time'],
                                        format='%j %H%M%S')

        # Drop the original jday and time columns
        df = df.drop(['jday', 'time'], axis=1)

        sequence_file_obj, created = Sequence.objects.get_or_create(
            linename=str(df['linename'].iloc[0]),
            defaults={
                'preplot_number': filename[0:4],
                'type': filename[4],
                'pass_number': filename[5],
                'sequence_number': filename[6:10],
                'filename': filename
            })

        # Create SequenceFileDetail instances
        sequence_file_details = []
        for _, row in df.iterrows():
            sequence_file_detail = AcquisitionShotPoint(
                sequence=sequence_file_obj,
                sp=row['sp'],
                lat=row['lat'],
                long=row['long'],
                east=row['east'],
                north=row['north'],
                depth=row['depth'],
                datetime=row['datetime'],
                zlat1=row['zlat1'],
                zlon1=row['zlon1'],
                zlat2=row['zlat2'],
                zlon2=row['zlon2'],
                zlat3=row['zlat3'],
                zlon3=row['zlon3'],
                mean_lat=row['mean lat'],
                mean_lon=row['mean lon'])
            sequence_file_details.append(sequence_file_detail)

        # Bulk create all SequenceFileDetail instances
        AcquisitionShotPoint.objects.bulk_create(sequence_file_details)

    finally:
        # Delete the temporary file
        default_storage.delete(file_path)

    return len(df)


class LoadSequenceView(View):

    def get(self, request):
        return render(request, 'planner/load_sequence.html')

    def post(self, request):
        try:
            if 'sequence_file' not in request.FILES:
                messages.error(request, 'No file was uploaded.')
                return redirect('load_sequence')

            sequence_files = request.FILES.getlist('sequence_file')
            total_files = len(sequence_files)

            if total_files > settings.DATA_UPLOAD_MAX_NUMBER_FILES:
                messages.error(
                    request,
                    f'Too many files. Maximum allowed is {settings.DATA_UPLOAD_MAX_NUMBER_FILES}.'
                )
                return redirect('load_sequence')

            files_to_process = []
            files_already_loaded = []

            for sequence_file in sequence_files:
                if not sequence_file.name.endswith('.p190'):
                    messages.error(
                        request,
                        f'Invalid file type for {sequence_file.name}. Please upload only .p190 files.'
                    )
                    continue

                # Check if file has already been loaded
                if Sequence.objects.filter(
                        sequence_number=sequence_file.name).exists():
                    files_already_loaded.append(sequence_file.name)
                    continue

                # Save the file using Django's storage system
                file_path = os.path.join('temp_sequences', sequence_file.name)
                full_path = default_storage.save(
                    file_path, ContentFile(sequence_file.read()))
                files_to_process.append(full_path)

            # Schedule background tasks for files to process
            for file_path in files_to_process:
                process_sequence_file(file_path, schedule=timezone.now())

            # Prepare messages
            if files_to_process:
                messages.success(
                    request,
                    f'Processing {len(files_to_process)} files in the background. Check back later for results.'
                )

            if files_already_loaded:
                messages.warning(
                    request,
                    f'The following files were already loaded and skipped: {", ".join(files_already_loaded)}'
                )

            if not files_to_process and not files_already_loaded:
                messages.error(request, 'No valid files were uploaded.')

            return redirect('display_points')

        except ValidationError as e:
            messages.error(request, f'Validation error: {str(e)}')
        except Exception as e:
            messages.error(request, f'An unexpected error occurred: {str(e)}')

        return redirect('load_sequence')
