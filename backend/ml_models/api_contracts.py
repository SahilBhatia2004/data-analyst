"""
API Contracts for AI Data Analyst Platform

This module defines the request/response contracts for all API endpoints
between frontend and backend.
"""


# Authentication API Contracts
AUTH_REQUESTS = {
    'login': {
        'required_fields': ['email', 'password'],
        'optional_fields': [],
        'description': 'User login request'
    },
    'signup': {
        'required_fields': ['email', 'password'],
        'optional_fields': ['first_name', 'last_name'],
        'description': 'User registration request'
    },
    'verify_token': {
        'required_fields': ['token'],
        'optional_fields': [],
        'description': 'Token verification request'
    }
}

AUTH_RESPONSES = {
    'login_success': {
        'status': 200,
        'data': {
            'token': 'string',
            'user': {
                'id': 'integer',
                'username': 'string',
                'email': 'string',
                'supabase_id': 'string'
            }
        }
    },
    'login_error': {
        'status': 401,
        'data': {
            'error': 'string'
        }
    },
    'signup_success': {
        'status': 201,
        'data': {
            'token': 'string',
            'user': {
                'id': 'integer',
                'username': 'string',
                'email': 'string',
                'supabase_id': 'string'
            }
        }
    },
    'signup_error': {
        'status': 400,
        'data': {
            'error': 'string'
        }
    }
}


# File Management API Contracts
FILE_REQUESTS = {
    'upload': {
        'method': 'POST',
        'content_type': 'multipart/form-data',
        'required_fields': ['file'],
        'optional_fields': [],
        'description': 'Upload Excel/CSV file'
    },
    'connect_google_sheet': {
        'method': 'POST',
        'content_type': 'application/json',
        'required_fields': ['sheet_url'],
        'optional_fields': ['sheet_name'],
        'description': 'Connect to Google Sheet'
    },
    'list_files': {
        'method': 'GET',
        'content_type': 'application/json',
        'required_fields': [],
        'optional_fields': [],
        'description': 'List user files'
    },
    'get_preview': {
        'method': 'GET',
        'content_type': 'application/json',
        'required_fields': [],
        'optional_fields': [],
        'description': 'Get file data preview'
    },
    'delete_file': {
        'method': 'DELETE',
        'content_type': 'application/json',
        'required_fields': [],
        'optional_fields': [],
        'description': 'Delete uploaded file'
    }
}

FILE_RESPONSES = {
    'upload_success': {
        'status': 201,
        'data': {
            'message': 'string',
            'file_id': 'integer',
            'file_name': 'string',
            'status': 'string'
        }
    },
    'upload_error': {
        'status': 400,
        'data': {
            'error': 'string'
        }
    },
    'list_success': {
        'status': 200,
        'data': {
            'files': [
                {
                    'id': 'integer',
                    'file_name': 'string',
                    'file_type': 'string',
                    'file_size': 'integer',
                    'uploaded_at': 'datetime',
                    'is_processed': 'boolean',
                    'processing_status': 'string',
                    'row_count': 'integer',
                    'column_count': 'integer'
                }
            ]
        }
    },
    'preview_success': {
        'status': 200,
        'data': {
            'file_name': 'string',
            'data_preview': {
                'columns': ['string'],
                'data': [['value']],
                'dtypes': {'column': 'type'},
                'null_counts': {'column': 'integer'},
                'unique_counts': {'column': 'integer'}
            },
            'row_count': 'integer',
            'column_count': 'integer'
        }
    }
}


# Chat API Contracts
CHAT_REQUESTS = {
    'send_message': {
        'method': 'POST',
        'content_type': 'application/json',
        'required_fields': ['message', 'file_id'],
        'optional_fields': ['session_id'],
        'description': 'Send chat message'
    }
}

CHAT_RESPONSES = {
    'message_success': {
        'status': 200,
        'data': {
            'response': 'string',
            'session_id': 'string',
            'sql_query': 'string',
            'data': [
                {
                    'column1': 'value',
                    'column2': 'value'
                }
            ]
        }
    },
    'message_error': {
        'status': 400,
        'data': {
            'error': 'string'
        }
    }
}


# Dashboard API Contracts
DASHBOARD_REQUESTS = {
    'generate': {
        'method': 'POST',
        'content_type': 'application/json',
        'required_fields': ['file_id'],
        'optional_fields': ['query', 'theme'],
        'description': 'Generate dashboard'
    },
    'get_dashboard': {
        'method': 'GET',
        'content_type': 'application/json',
        'required_fields': [],
        'optional_fields': [],
        'description': 'Get existing dashboard'
    },
    'export': {
        'method': 'POST',
        'content_type': 'application/json',
        'required_fields': ['format'],
        'optional_fields': [],
        'description': 'Export dashboard'
    }
}

DASHBOARD_RESPONSES = {
    'generate_success': {
        'status': 201,
        'data': {
            'dashboard_id': 'string',
            'dashboard_data': {
                'title': 'string',
                'sections': [
                    {
                        'title': 'string',
                        'type': 'string',
                        'cards': [
                            {
                                'type': 'string',
                                'title': 'string',
                                'value': 'string',
                                'description': 'string'
                            }
                        ],
                        'charts': [
                            {
                                'type': 'string',
                                'title': 'string',
                                'data': 'object',
                                'height': 'integer'
                            }
                        ]
                    }
                ],
                'narrative': 'string'
            },
            'insights': {
                'kpis': ['object'],
                'trends': ['object'],
                'anomalies': ['object'],
                'correlations': ['object']
            }
        }
    },
    'get_success': {
        'status': 200,
        'data': {
            'dashboard_id': 'string',
            'dashboard_data': 'object',
            'theme': 'object',
            'created_at': 'datetime'
        }
    },
    'export_success': {
        'status': 200,
        'data': {
            'export_id': 'string',
            'export_link': 'string',
            'format': 'string'
        }
    }
}


# Theme/Color API Contracts
THEME_REQUESTS = {
    'get_color_grid': {
        'method': 'GET',
        'content_type': 'application/json',
        'required_fields': [],
        'optional_fields': [],
        'description': 'Get available color options'
    },
    'preview_theme': {
        'method': 'POST',
        'content_type': 'application/json',
        'required_fields': ['text_color', 'chart_color', 'background_color'],
        'optional_fields': [],
        'description': 'Preview theme with selected colors'
    }
}

THEME_RESPONSES = {
    'color_grid': {
        'status': 200,
        'data': {
            'color_grid': [
                {
                    'base': 'string',
                    'variations': ['string']
                }
            ],
            'presets': [
                {
                    'name': 'string',
                    'text': 'string',
                    'chart': 'string',
                    'background': 'string'
                }
            ]
        }
    },
    'theme_preview': {
        'status': 200,
        'data': {
            'theme': {
                'colors': {
                    'primary': 'string',
                    'text': 'string',
                    'background': 'string',
                    'chart': 'string'
                }
            },
            'contrast_ratio': 'float',
            'accessibility': 'string'
        }
    }
}


# Error Response Contract
ERROR_RESPONSE = {
    'status': 400,
    'data': {
        'error': 'string',
        'details': 'string (optional)',
        'code': 'string (optional)'
    }
}


# Success Response Contract
SUCCESS_RESPONSE = {
    'status': 200,
    'data': {
        'message': 'string',
        'data': 'object (optional)'
    }
}


# API Version Contract
API_VERSION = {
    'version': '1.0.0',
    'endpoints': {
        'auth': AUTH_REQUESTS,
        'files': FILE_REQUESTS,
        'chat': CHAT_REQUESTS,
        'dashboard': DASHBOARD_REQUESTS,
        'theme': THEME_REQUESTS
    },
    'responses': {
        'auth': AUTH_RESPONSES,
        'files': FILE_RESPONSES,
        'chat': CHAT_RESPONSES,
        'dashboard': DASHBOARD_RESPONSES,
        'theme': THEME_RESPONSES,
        'error': ERROR_RESPONSE,
        'success': SUCCESS_RESPONSE
    }
}


def validate_request(endpoint, request_data, method='POST'):
    """
    Validate request data against API contract.

    Args:
        endpoint (str): API endpoint name
        request_data (dict): Request data to validate
        method (str): HTTP method

    Returns:
        dict: Validation result with errors if any
    """
    validation_result = {
        'valid': True,
        'errors': []
    }

    # Get endpoint contract
    endpoint_contract = None

    if endpoint in AUTH_REQUESTS:
        endpoint_contract = AUTH_REQUESTS[endpoint]
    elif endpoint in FILE_REQUESTS:
        endpoint_contract = FILE_REQUESTS[endpoint]
    elif endpoint in CHAT_REQUESTS:
        endpoint_contract = CHAT_REQUESTS[endpoint]
    elif endpoint in DASHBOARD_REQUESTS:
        endpoint_contract = DASHBOARD_REQUESTS[endpoint]
    elif endpoint in THEME_REQUESTS:
        endpoint_contract = THEME_REQUESTS[endpoint]

    if not endpoint_contract:
        validation_result['errors'].append(f"Unknown endpoint: {endpoint}")
        validation_result['valid'] = False
        return validation_result

    # Check required fields
    for field in endpoint_contract.get('required_fields', []):
        if field not in request_data:
            validation_result['errors'].append(f"Required field missing: {field}")
            validation_result['valid'] = False

    return validation_result


def get_response_contract(endpoint, response_type='success'):
    """
    Get response contract for an endpoint.

    Args:
        endpoint (str): API endpoint name
        response_type (str): Type of response ('success' or 'error')

    Returns:
        dict: Response contract
    """
    if endpoint in AUTH_RESPONSES and response_type in AUTH_RESPONSES[endpoint]:
        return AUTH_RESPONSES[endpoint][response_type]
    elif endpoint in FILE_RESPONSES and response_type in FILE_RESPONSES[endpoint]:
        return FILE_RESPONSES[endpoint][response_type]
    elif endpoint in CHAT_RESPONSES and response_type in CHAT_RESPONSES[endpoint]:
        return CHAT_RESPONSES[endpoint][response_type]
    elif endpoint in DASHBOARD_RESPONSES and response_type in DASHBOARD_RESPONSES[endpoint]:
        return DASHBOARD_RESPONSES[endpoint][response_type]
    elif endpoint in THEME_RESPONSES and response_type in THEME_RESPONSES[endpoint]:
        return THEME_RESPONSES[endpoint][response_type]

    return SUCCESS_RESPONSE if response_type == 'success' else ERROR_RESPONSE
