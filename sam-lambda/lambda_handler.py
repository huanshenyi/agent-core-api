import boto3
import json
import os
import uuid
from typing import Dict, Any

from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)

# Initialize LINE Bot API configuration globally
LINE_CONFIGURATION = None
if 'LINE_CHANNEL_ACCESS_TOKEN' in os.environ:
    LINE_CONFIGURATION = Configuration(access_token=os.environ['LINE_CHANNEL_ACCESS_TOKEN'])

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for Bedrock AgentCore with LINE Message API support
    """
    
    try:
        # Parse request body
        if 'body' not in event:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Missing request body'})
            }
        
        # Parse JSON body
        body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        
        # Check if this is a LINE webhook event
        if 'events' in body and len(body['events']) > 0:
            return handle_line_webhook(body)
        
        # Original API Gateway handling
        prompt = body.get('prompt', 'Hello')
        
        # Call bedrock-agentcore
        result = call_bedrock_agentcore(prompt)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'result': result
            })
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }

def handle_line_webhook(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle LINE webhook events
    """
    try:
        if body['events'][0]['type'] == 'message':
            if body['events'][0]['message']['type'] == 'text':
                message = body['events'][0]['message']['text']
                
                # Call bedrock-agentcore
                result = call_bedrock_agentcore(message)
                
                # Send reply via LINE
                if LINE_CONFIGURATION:
                    # Ensure result is a string
                    text_result = str(result)
                    print(f"DEBUG: Sending LINE message: {text_result}")
                    
                    try:
                        with ApiClient(LINE_CONFIGURATION) as api_client:
                            line_bot_api = MessagingApi(api_client)
                            line_bot_api.reply_message_with_http_info(
                                ReplyMessageRequest(
                                    reply_token=body['events'][0]['replyToken'],
                                    messages=[TextMessage(text=text_result)]
                                )
                            )
                        print("DEBUG: LINE message sent successfully")
                    except Exception as line_error:
                        print(f"ERROR: Failed to send LINE message: {str(line_error)}")
                else:
                    print("ERROR: LINE_CONFIGURATION not initialized")
    
    except Exception as e:
        print(f"ERROR: LINE webhook processing failed: {str(e)}")
    
    return {
        'statusCode': 200,
        'body': json.dumps('Success!')
    }

def call_bedrock_agentcore(prompt: str) -> str:
    """
    Call Bedrock AgentCore and return the result
    """
    # Initialize the Bedrock AgentCore client
    agent_core_client = boto3.client('bedrock-agentcore')
    
    # Get agent runtime ARN from environment
    agent_arn = os.environ.get('BEDROCK_AGENT_RUNTIME_ARN')
    if not agent_arn:
        return 'Agent runtime ARN not configured'
    
    # Prepare the payload
    payload = json.dumps({"prompt": prompt}).encode()
    
    # Debug: Log request parameters
    print(f"DEBUG: Agent ARN: {agent_arn}")
    print(f"DEBUG: Prompt: {prompt}")
    print(f"DEBUG: Payload: {payload}")
    
    # Invoke the agent (correct JSON format)
    response = agent_core_client.invoke_agent_runtime(
        agentRuntimeArn=agent_arn,
        contentType="application/json",
        payload=payload,
        traceId=str(uuid.uuid4()).replace('-', ''),
    )
    
    # Debug: Log response structure
    print(f"DEBUG: Response keys: {list(response.keys())}")
    print(f"DEBUG: Response contentType: {response.get('contentType', 'N/A')}")
    print(f"DEBUG: Response statusCode: {response.get('statusCode', 'N/A')}")
    
    # Log the raw response data
    if 'response' in response:
        print(f"DEBUG: Raw response data type: {type(response['response'])}")
        if hasattr(response['response'], '__len__'):
            print(f"DEBUG: Raw response data length: {len(response['response'])}")
    
    # Process the response
    result = process_response(response)
    
    # Extract text content from the result
    print(f"DEBUG: Extracting text from result: {result}")
    print(f"DEBUG: Result type: {type(result)}")
    
    if isinstance(result, dict) and 'result' in result:
        print("DEBUG: Found 'result' key in result")
        inner_result = result['result']
        print(f"DEBUG: Inner result: {inner_result}")
        print(f"DEBUG: Inner result type: {type(inner_result)}")
        
        if isinstance(inner_result, dict) and 'content' in inner_result:
            print("DEBUG: Found 'content' key in inner result")
            content = inner_result['content']
            print(f"DEBUG: Content: {content}")
            print(f"DEBUG: Content type: {type(content)}")
            
            if isinstance(content, list) and len(content) > 0:
                print(f"DEBUG: Content is list with {len(content)} items")
                first_item = content[0]
                print(f"DEBUG: First item: {first_item}")
                print(f"DEBUG: First item type: {type(first_item)}")
                
                if isinstance(first_item, dict) and 'text' in first_item:
                    extracted_text = first_item['text']
                    print(f"DEBUG: Extracted text: {extracted_text}")
                    return extracted_text
                else:
                    print("DEBUG: First item is not dict or doesn't have 'text' key")
            else:
                print("DEBUG: Content is not list or is empty")
        else:
            print("DEBUG: Inner result is not dict or doesn't have 'content' key")
    else:
        print("DEBUG: Result is not dict or doesn't have 'result' key")
    
    # Fallback to string conversion
    fallback_result = str(result)
    print(f"DEBUG: Fallback to string conversion: {fallback_result}")
    return fallback_result

def process_response(response: Dict[str, Any]) -> Any:
    """
    Process and return the response from Bedrock AgentCore
    """
    try:
        print(f"DEBUG: process_response input: {response}")
        print(f"DEBUG: contentType: {response.get('contentType', 'N/A')}")
        print(f"DEBUG: response keys: {list(response.keys())}")
        
        # Handle streaming response
        if "text/event-stream" in response.get("contentType", ""):
            print("DEBUG: Processing streaming response")
            content = []
            for line in response["response"].iter_lines(chunk_size=10):
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        line = line[6:]
                        content.append(line)
            result = "\n".join(content)
            print(f"DEBUG: Streaming result: {result}")
            # Try to parse as JSON first
            try:
                parsed = json.loads(result)
                print(f"DEBUG: Parsed streaming JSON: {parsed}")
                return parsed
            except:
                print(f"DEBUG: Streaming fallback to string: {result}")
                return result
        
        # Handle standard JSON response
        elif response.get("contentType") == "application/json":
            print("DEBUG: Processing JSON response")
            content = []
            response_data = response.get("response", [])
            print(f"DEBUG: response data type: {type(response_data)}")
            print(f"DEBUG: response data: {response_data}")
            
            for chunk in response_data:
                decoded_chunk = chunk.decode('utf-8')
                print(f"DEBUG: decoded chunk: {decoded_chunk}")
                content.append(decoded_chunk)
            
            full_content = ''.join(content)
            print(f"DEBUG: Full content: {full_content}")
            
            parsed_result = json.loads(full_content)
            print(f"DEBUG: Parsed JSON result: {parsed_result}")
            return parsed_result
        
        # Handle other content types
        else:
            print(f"DEBUG: Other content type, returning raw response")
            return response
            
    except Exception as e:
        error_msg = f"Error processing response: {str(e)}"
        print(f"DEBUG: Exception in process_response: {error_msg}")
        return error_msg