import os
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.shortcuts import render
from django.views import View
from django.contrib import messages
from .models import File, PreplotShotPoints, Polygon, PreplotLine
from .models import Sequence, AcquisitionShotPoint
import json
from django.shortcuts import redirect
from .functions import (
    srecords_to_df,
    get_preplot_coordinates,
    get_preplot_shots,
    get_4d_preplot,
    get_4d_preplot_endpoints,
    # Add other specific functions you need
)
import pandas as pd
from django.core.exceptions import ValidationError
from django.conf import settings
from django.http import JsonResponse
from celery import shared_task
import io
from django.views.generic import TemplateView
from django.db.models import Min, Max
from datetime import timedelta


class HomeView(View):

    def get(self, request):
        # def get(self, request):
        files = File.objects.all()
        points = PreplotShotPoints.objects.all()
        polygon = Polygon.objects.first()
        sequences = Sequence.objects.all().order_by('sequence_number')

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
                    'date': first_point.datetime.strftime('%Y-%m-%d %H:%M:%S'),
                    'point_type': 'First'
                }, {
                    'lat': last_point.mean_lat,
                    'lon': last_point.mean_lon,
                    'sp': last_point.sp,
                    'depth': last_point.depth,
                    'sequence_name': sequence.linename,
                    'date': last_point.datetime.strftime('%Y-%m-%d %H:%M:%S'),
                    'point_type': 'Last'
                }])

        line_change_times = []

        for i in range(len(sequences) - 1):
            current_seq = sequences[i]
            next_seq = sequences[i + 1]

            # Get last point of current sequence
            last_point = AcquisitionShotPoint.objects.filter(
                sequence=current_seq).order_by('datetime').last()

            # Get first point of next sequence
            first_point = AcquisitionShotPoint.objects.filter(
                sequence=next_seq).order_by('datetime').first()

            if last_point and first_point:
                # Calculate time difference in minutes
                time_diff = first_point.datetime - last_point.datetime
                minutes = time_diff.total_seconds() / 60

                line_change_times.append({
                    'from_sequence': current_seq.sequence_number,
                    'to_sequence': next_seq.sequence_number,
                    'duration_minutes': round(minutes, 1)
                })

        # context['line_change_times'] = json.dumps(line_change_times)

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
            'shotpoint2': line.shotpoint2,
            'completed': line.calculate_completion_status()
        } for line in lines]

        context = {
            'files': files,
            'points': points,
            'polygon': polygon,
            'preplot_lines': json.dumps(lines_data),
            'sequence_points': json.dumps(sequence_points),
            'line_change_times': json.dumps(line_change_times)
        }
        return render(request, 'planner/home.html', context)




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
        print("Request data:", request.POST)  # Output the POST data
        print("Files uploaded:", request.FILES)  # Output the uploaded files

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
            fourd_preplot = request.FILES['preplot_file']

            # Validate the file extension
            if not fourd_preplot.name.endswith('.p190'):
                messages.error(
                    request, 'Invalid file type. Please upload a .p190 file.')
                return redirect('load_preplot')

            # Process the preplot file for 4D type
            df = get_4d_preplot(fourd_preplot)

            fourd_df = df[df['source_number'] == '2']
            preplot_lines_df = get_4d_preplot_endpoints(fourd_df)

            preplot_lines = []

            # Check for existing preplot lines to avoid duplicate creation
            existing_lines = set(
                PreplotLine.objects.values_list('preplot', flat=True))

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
                f'Successfully loaded {fourd_preplot.name}. Processed {len(preplot_lines)} new lines.'
            )

        return redirect('home')  # Redirect after successful upload


@shared_task
def process_sequence_file(file_path):
    try:
        # Read the file content in a way that ensures the file handle is properly closed
        file_content = None
        try:
            with default_storage.open(file_path, 'rb') as file:
                file_content = file.read()
        except Exception as e:
            print(f"Error reading file: {e}")
            raise

        if file_content is None:
            raise ValueError("Could not read file content")

        # Convert the content to StringIO or process it directly
        df = srecords_to_df(io.BytesIO(file_content))

        filename = os.path.basename(file_path)
        linename = str(df['linename'].iloc[0])
        preplot_number = int(linename[0:4])

        # Add debug print
        # print(f"Linename: {linename}, Length: {len(linename)}")

        # Find the corresponding PreplotLine
        try:
            preplot_line = PreplotLine.objects.get(preplot=preplot_number)
        except PreplotLine.DoesNotExist:
            print(f"No PreplotLine found for preplot number {preplot_number}")
            return

        # Convert jday and time to a single datetime column
        # df['datetime'] = pd.to_datetime(df['jday'].astype(str) + ' ' +
        #                                 df['time'],
        #                                 format='%j %H%M%S')

        # Drop the original jday and time columns
        df = df.drop(['jday', 'time'], axis=1)
        # print(df.head())

        # Create sequence with proper integer conversion
        sequence_file_obj, created = Sequence.objects.get_or_create(
            linename=linename,
            defaults={
                'type': int(linename[4]),
                'pass_number': int(linename[5]),
                'sequence_number': int(linename[6:10]),
                'filename': filename,
                'preplot': preplot_line
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
                datetime=row['dt'],
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

    except Exception as e:
        print(f"Error processing file: {e}")
        raise
    finally:
        try:
            # Clean up the temporary file
            default_storage.delete(file_path)
        except Exception as e:
            print(f"Error deleting temporary file: {e}")

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

            # Check if the 'temp_sequences' directory exists, if not, create it
            temp_sequences_dir = os.path.join(settings.MEDIA_ROOT,
                                              'temp_sequences')
            if not os.path.exists(temp_sequences_dir):
                os.makedirs(temp_sequences_dir)

            for sequence_file in sequence_files:
                if not sequence_file.name.endswith('.p190'):
                    messages.error(
                        request,
                        f'Invalid file type for {sequence_file.name}. Please upload only .p190 files.'
                    )
                    continue

                # Check if file has already been loaded
                if Sequence.objects.filter(
                        sequence_number=sequence_file.name[6:10]).exists():
                    files_already_loaded.append(sequence_file.name)
                    continue

                # Save the file using Django's storage system
                file_path = os.path.join('temp_sequences', sequence_file.name)
                full_path = default_storage.save(
                    file_path, ContentFile(sequence_file.read()))
                files_to_process.append(full_path)

            # Schedule background tasks for files to process
            for file_path in files_to_process:
                print(file_path)
                process_sequence_file(
                    file_path)  # Using .delay() to run as async task
            # Prepare messages

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

            return redirect('home')

        except ValidationError as e:
            messages.error(request, f'Validation error: {str(e)}')
        except Exception as e:
            messages.error(request, f'An unexpected error occurred: {str(e)}')

        return redirect('load_sequence')


class StatsView(TemplateView):
    template_name = 'planner/stats.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get all sequences ordered by sequence number
        sequences = Sequence.objects.all().order_by('sequence_number')
        line_change_times = []

        for i in range(len(sequences) - 1):
            current_seq = sequences[i]
            next_seq = sequences[i + 1]

            # Get last point of current sequence
            last_point = AcquisitionShotPoint.objects.filter(
                sequence=current_seq).order_by('datetime').last()

            # Get first point of next sequence
            first_point = AcquisitionShotPoint.objects.filter(
                sequence=next_seq).order_by('datetime').first()

            if last_point and first_point:
                # Calculate time difference in minutes
                time_diff = first_point.datetime - last_point.datetime
                minutes = time_diff.total_seconds() / 60

                line_change_times.append({
                    'from_sequence': current_seq.sequence_number,
                    'to_sequence': next_seq.sequence_number,
                    'duration_minutes': round(minutes, 1)
                })

        context['line_change_times'] = json.dumps(line_change_times)
        return context

    def post(self, request, *args, **kwargs):
        if 'preplot_file' not in request.FILES:
            messages.error(request, 'No file uploaded')
            return redirect('stats')

        uploaded_file = request.FILES['preplot_file']
        try:
            # Process the file using get_4d_preplot
            df = get_4d_preplot(uploaded_file)
            print(df.head())  # Debug print

            # Create PreplotShotPoints objects
            preplot_points = []
            preplot_lines = {
                pl.preplot: pl
                for pl in PreplotLine.objects.all()
            }
            for _, row in df.iterrows():
                preplot_id = int(row['preplot_line'])
                preplot_line = preplot_lines.get(preplot_id)
                if preplot_line:
                    point = PreplotShotPoints(
                        preplot=preplot_line,
                        shotpoint=int(row['shotpoint']),
                        easting=float(row['easting']),
                        northing=float(row['northing']),
                        latitude=float(row['latitude']),
                        longitude=float(row['longitude']),
                        source_number=row['source_number'])
                    preplot_points.append(point)

            # Bulk create all points
            PreplotShotPoints.objects.bulk_create(preplot_points)
            return JsonResponse({
                'success':
                True,
                'message':
                f'Successfully loaded {len(preplot_points)} preplot points'
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
