-- top tags
select name, count(tag_id) as count from bookmark_tags,tags where tags.id=bookmark_tags.tag_id group by tag_id  order by count desc;

