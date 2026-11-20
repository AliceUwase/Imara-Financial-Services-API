from django.http import JsonResponse


def health(request):
	"""Simple health endpoint required by the autograder.

	Returns HTTP 200 with a small JSON body.
	"""
	return JsonResponse({'status': 'ok'})
