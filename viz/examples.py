EXAMPLES = {
    "2 nodes: rulebook changes winner": """{
  "rules": ["dist", "energy"],
  "rulebook": { "edges": [["dist", "energy"]] },
  "graph": {
    "edges": [
      {"u":"S","v":"A","c":[5,100]},
      {"u":"A","v":"T","c":[5,100]},
      {"u":"S","v":"B","c":[6,1]},
      {"u":"B","v":"T","c":[6,1]}
    ]
  },
  "start": "S",
  "goal": "T",
  "eps": [0,0]
}""",

    "3 nodes: incomparable rule": """{
  "rules": ["r1", "r2", "r3", "r4"],
  "rulebook": { "edges": [["r1", "r2"], ["r1", "r3"]] },
  "graph": {
    "edges": [
      {"u":"S","v":"A","c":[5,10,10,100]},
      {"u":"A","v":"T","c":[5,10,10,100]},
      {"u":"S","v":"B","c":[6,1,1,1]},
      {"u":"B","v":"T","c":[6,1,1,1]},
      {"u":"S","v":"C","c":[5,20,20,5]},
      {"u":"C","v":"T","c":[5,20,20,5]}
    ]
  },
  "start": "S",
  "goal": "T",
  "eps": [0,0,0,0]
}""",

    "6 nodes: mixed paths w/ tradeoffs": """{
  "rules": ["safety", "dist", "energy"],
  "rulebook": { "edges": [["safety", "dist"], ["safety", "energy"]] },
  "graph": {
    "edges": [
      {"u":"S","v":"A","c":[1,8,8]},
      {"u":"S","v":"B","c":[2,3,2]},
      {"u":"S","v":"C","c":[1,10,1]},
      {"u":"A","v":"D","c":[1,2,2]},
      {"u":"A","v":"E","c":[2,1,5]},
      {"u":"B","v":"D","c":[2,2,2]},
      {"u":"B","v":"E","c":[1,5,1]},
      {"u":"C","v":"D","c":[2,1,6]},
      {"u":"C","v":"E","c":[1,4,1]},
      {"u":"D","v":"T","c":[1,2,2]},
      {"u":"E","v":"T","c":[1,1,1]}
    ]
  },
  "start": "S",
  "goal": "T",
  "eps": [0,0,0]
}"""
}