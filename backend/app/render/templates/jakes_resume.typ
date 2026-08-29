#set page(paper: "us-letter", margin: (x: 0.62in, y: 0.54in))
#set text(size: 9.4pt, lang: cv.output_language)
#set par(justify: true, leading: 0.48em)

#let section(title) = {
  v(7pt)
  text(weight: "bold", size: 11pt, title)
  v(1pt)
  line(length: 100%, stroke: 0.55pt)
  v(3pt)
}

#let entry(item) = {
  if item.title != "" {
    text(weight: "bold", item.title)
    linebreak()
  }
  item.content
  if item.technologies.len() > 0 {
    linebreak()
    text(size: 8.2pt, fill: rgb("#4b5563"), item.technologies.join(", "))
  }
  v(4pt)
}

#align(center)[
  #text(size: 19pt, weight: "bold", cv.name)
  #linebreak()
  #text(size: 8.7pt, cv.contact.join(" | "))
]

#if cv.summary != "" {
  section(if cv.output_language == "tr" { "Ozet" } else { "Summary" })
  cv.summary
}

#if cv.experience.len() > 0 {
  section(if cv.output_language == "tr" { "Deneyim" } else { "Experience" })
  for item in cv.experience {
    entry(item)
  }
}

#if cv.projects.len() > 0 {
  section(if cv.output_language == "tr" { "Projeler" } else { "Projects" })
  for item in cv.projects {
    entry(item)
  }
}

#if cv.skills.len() > 0 {
  section(if cv.output_language == "tr" { "Beceriler" } else { "Skills" })
  for item in cv.skills {
    entry(item)
  }
}

#if cv.education.len() > 0 {
  section(if cv.output_language == "tr" { "Egitim" } else { "Education" })
  for item in cv.education {
    entry(item)
  }
}
