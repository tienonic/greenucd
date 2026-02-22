---
permalink: /
layout: default
title: GREEN at UC Davis
---

<div id="about" class="row" style="margin-top: 20px;" markdown="1">
<div class="col-md-8" markdown="1">

## Welcome to GREEN at UC Davis

**GREEN (Green Innovation Network)** is a student-led AgTech organization at UC Davis passionate about tackling environmental and agricultural technology challenges through collaboration, hands-on projects, and cutting-edge research.

We organize workshops, speaker series, and projects focused on sustainable agriculture, renewable energy, and environmental conservation. Join UC Davis's premier green tech club to connect, create, and drive change toward a greener future.

</div>
<div class="col-md-4" markdown="1">
**Contact:** [greenucd@gmail.com](mailto:greenucd@gmail.com)

**Instagram:** [@green.ucd](https://www.instagram.com/green.ucd/)

**Discord:** [Join our server](https://discord.com/invite/5krgBsWp3r)
</div>
</div>

---

<div id="calendar" style="margin: 30px 0;">
<h2>Events Calendar</h2>
<iframe src="https://calendar.google.com/calendar/embed?showTitle=0&showNav=1&showPrint=0&showCalendars=0&mode=AGENDA&height=250&wkst=1&bgcolor=%23FFFFFF&src=61d8f01d5d00cb5bd304badc76c060acfa87badf0c68b180d1a0b78150cc9b2c%40group.calendar.google.com&color=%23125A12&ctz=America%2FLos_Angeles" style="border-width:0" width="100%" height="250" frameborder="0" scrolling="no"></iframe>
</div>

---

<div id="board" style="margin: 30px 0;">
<h2>Board Members</h2>
<div class="row">
  {% assign exec = site.data.positions[0] %}
  {% for position in exec.positions %}
    {% for officer_id in position.officers %}
      {% assign officer = site.data.officers[officer_id] %}
      <div class="col-md-3 col-sm-6" style="margin-bottom: 20px; text-align: center;">
        <div class="thumbnail" style="padding: 15px;">
          <img src="/images/leaders/{{ officer.photo | default: 'beaver.jpg' }}" alt="{{ officer.name }}" class="img-circle" style="width:80px; height:80px; object-fit:cover; margin: 0 auto 10px;">
          <h4 style="margin: 5px 0;">{{ officer.name }}</h4>
          <p style="color: #666; margin: 0;">{{ position.title }}</p>
        </div>
      </div>
    {% endfor %}
  {% endfor %}
</div>

</div>
