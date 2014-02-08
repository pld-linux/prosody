# TODO
# - register uid/gid
# - register group (default "users" is not fine!)
# - bashism in %post
Summary:	Flexible communications server for Jabber/XMPP
Name:		prosody
Version:	0.9.2
Release:	0.1
License:	MIT
Group:		Daemons
Source0:	http://prosody.im/downloads/source/%{name}-%{version}.tar.gz
# Source0-md5:	bb91f73be0e19d049f1a57951b52c3a2
Source1:	%{name}.init
Source2:	%{name}.tmpfiles
Source3:	%{name}.service
URL:		http://prosody.im/
BuildRequires:	libidn-devel
BuildRequires:	lua51-devel
BuildRequires:	openssl-devel
BuildRequires:	rpmbuild(macros) >= 1.647
BuildRequires:	sed >= 4.0
BuildRequires:	systemd-units
Requires:	lua-dbi
Requires:	lua-expat
Requires:	lua-filesystem
Requires:	lua-sec
Requires:	systemd-units >= 0.38
Requires(post,preun,postun):	systemd-units >= 38
BuildRoot:	%{tmpdir}/%{name}-%{version}-root-%(id -u -n)

%description
Prosody is a flexible communications server for Jabber/XMPP written in
Lua. It aims to be easy to use, and light on resources. For developers
it aims to be easy to extend and give a flexible system on which to
rapidly develop added functionality, or prototype new protocols.

%prep
%setup -q
sed -e 's|$(PREFIX)/lib|$(PREFIX)/%{_lib}|' -i Makefile
# fix wrong end of line encoding
sed -i -e 's|\r||g' doc/stanza.txt doc/session.txt doc/roster_format.txt

%build
./configure \
  --with-lua-include=%{_includedir}/lua51 \
  --lua-suffix=51 \
  --prefix=%{_prefix}
%{__make} \
	CC=%{__cc} \
	CFLAGS="%{rpmcflags} -fPIC"

%install
rm -rf $RPM_BUILD_ROOT
%{__make} install \
	DESTDIR=$RPM_BUILD_ROOT

# fix perms
chmod -x $RPM_BUILD_ROOT%{_libdir}/%{name}/%{name}.version

# avoid rpmlint unstripped-binary-or-object warnings
chmod 0755 $RPM_BUILD_ROOT%{_libdir}/%{name}/util/*.so

# directories for datadir and pids
install -d $RPM_BUILD_ROOT{%{_sharedstatedir}/%{name},%{_localstatedir}/run/%{name}}

# systemd stuff
install -d $RPM_BUILD_ROOT%{systemdunitdir}
cp -p %{SOURCE3} $RPM_BUILD_ROOT%{systemdunitdir}/%{name}.service

# tmpfiles.d stuff
install -d $RPM_BUILD_ROOT%{systemdtmpfilesdir}
cp -p %{SOURCE2} $RPM_BUILD_ROOT%{systemdtmpfilesdir}/%{name}.conf

# install initd script
install -d $RPM_BUILD_ROOT/etc/rc.d/init.d
install -p %{SOURCE1} $RPM_BUILD_ROOT/etc/rc.d/init.d/%{name}

%clean
rm -rf $RPM_BUILD_ROOT

%pre
%useradd -u xxx -d %{_sharedstatedir}/%{name} -c "prosody daemon" %{name} -g XXX

%preun
if [ "$1" = "0" ]; then
	/sbin/chkconfig --del prosody
	%service -q prosody stop
fi
%systemd_preun prosody.service

%post
umask 077
if [ ! -f %{sslkey} ]; then
	%{_bindir}/openssl genrsa 1024 > %{sslkey} 2> /dev/null
	chown root:%{name} %{sslkey}
	chmod 640 %{sslkey}
fi

if [ ! -f %{sslcert} ]; then
	FQDN=`hostname`
	if [ "x${FQDN}" = "x" ]; then
		FQDN=localhost.localdomain
	fi

	# FIXME: $RANDOM is bashism!
	cat << -EOF | %{_bindir}/openssl req -new -key %{sslkey} \
	 -x509 -days 365 -set_serial $RANDOM \
	 -out %{sslcert} 2>/dev/null
	--
	SomeState
	SomeCity
	SomeOrganization
	SomeOrganizationalUnit
	${FQDN}
	root@${FQDN}
	EOF
	chmod 644 %{sslcert}
fi

/sbin/chkconfig --add prosody
%service prosody restart
%systemd_post prosody.service

%postun
if [ "$1" = "0" ]; then
	%userremove %{name}
fi
%systemd_reload

%files
%defattr(644,root,root,755)
%doc AUTHORS COPYING HACKERS README TODO doc/*
%attr(755,root,root) %{_bindir}/%{name}
%attr(755,root,root) %{_bindir}/%{name}ctl
%{_mandir}/man1/*.1*
%attr(754,root,root) /etc/rc.d/init.d/%{name}
%dir %{_libdir}/%{name}
%{_libdir}/%{name}/core
%{_libdir}/%{name}/modules
%{_libdir}/%{name}/net
%{_libdir}/%{name}/util
%{_libdir}/%{name}/prosody.version
%dir %{_sysconfdir}/%{name}
%dir %{_sysconfdir}/%{name}/certs
%config(noreplace) %attr(640,root,prosody) %{_sysconfdir}/%{name}/certs/example.com.cnf
%config(noreplace) %attr(640,root,prosody) %{_sysconfdir}/%{name}/certs/example.com.crt
%config(noreplace) %attr(640,root,prosody) %{_sysconfdir}/%{name}/certs/example.com.key
%config(noreplace) %attr(640,root,prosody) %{_sysconfdir}/%{name}/certs/localhost.cnf
%config(noreplace) %attr(640,root,prosody) %{_sysconfdir}/%{name}/certs/localhost.crt
%config(noreplace) %attr(640,root,prosody) %{_sysconfdir}/%{name}/certs/localhost.key
%config(noreplace) %attr(640,root,prosody) %{_sysconfdir}/%{name}/certs/openssl.cnf
%config(noreplace) %attr(640,root,prosody) %{_sysconfdir}/%{name}/certs/Makefile
%config(noreplace) %attr(640,root,prosody) %{_sysconfdir}/%{name}/prosody.cfg.lua
%{systemdtmpfilesdir}/prosody.conf
%{systemdunitdir}/prosody.service
%dir %attr(755,prosody,prosody) %{_sharedstatedir}/prosody
%dir %attr(755,prosody,prosody) %{_localstatedir}/run/prosody
