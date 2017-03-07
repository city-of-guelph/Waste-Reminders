var gulp = require('gulp'),
    del = require('del'),
    zip = require('gulp-zip'),
    lint = require('gulp-jshint'),
    htmlmin = require('gulp-htmlmin');

gulp.task('clean', function() {
  return del(['.tmp','dist','*.zip']);
});

gulp.task('jshint', function() {
  return gulp.src('app/static/js/*.js')
    .pipe(lint())
    .pipe(lint.reporter('jshint-stylish'))
    .pipe(lint.reporter('fail'));
});

gulp.task('html',function() {
  gulp.src('app/templates/**/*.html', {base:'.'})
    .pipe(htmlmin({collapseWhitespace:true}))
    .pipe(gulp.dest('dist'));
});

gulp.task('copy', ['clean','jshint'], function() {
  var st = gulp.src(
      ['app/**/*.*',
      '*.py',
      'requirements.txt',
      'logging.conf',
      'startgu.sh',
      '!app/Logo.pdn'], {base: '.'})
    .pipe(gulp.dest('dist'));

  return st;
});

gulp.task('zip', ['clean','copy'], function() {
  var st = gulp.src(['dist/**','!dist/app/data/*.txt','!dist/app/data/config.ini'])
    .pipe(zip('wastereminder.zip'))
    .pipe(gulp.dest('.'));

  return st;
});

gulp.task('zipdata', ['clean','copy'], function() {
  var st = gulp.src(['dist/app/data/*.txt','dist/app/data/config.ini'], {base: 'dist'})
    .pipe(zip('wastereminder_data.zip'))
    .pipe(gulp.dest('.'));

  return st;
});

gulp.task('build',['zip','zipdata']);

gulp.task('default', ['build']);
