exports = async function(changeEvent) {
    const body = {
    'providerSettings': {
        'providerName' : 'GCP',
        'diskIOPS': 3000,
        'instanceSizeName': "M30"
    },
    "diskSizeGB": 20
  }

  const arg = { 
    scheme: 'https', 
    host: 'cloud.mongodb.com', 
    path: 'api/atlas/v1.0/groups/<your-project-id>/clusters/<your-cluster-name>', 
    username:context.values.get('AtlasUser'), //retrieve username from secrets
    password: context.values.get('AtlasPassword'), //retrieve password from secrets
    headers: {'Content-Type': ['application/json'], 'Accept-Encoding': ['bzip, deflate']}, 
    digestAuth:true,
    body: JSON.stringify(body)
  };
  
  // The response body is a BSON.Binary object. Parse it and return.
  response = await context.http.patch(arg);

  return EJSON.parse(response.body.text()); 
};
